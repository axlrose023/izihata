import hashlib
import hmac
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.api.modules.orders.models import Order
from app.api.modules.payments.service import WayForPayProvider
from app.settings import WayForPayConfig

pytestmark = pytest.mark.asyncio
SECRET = "test-payment-key"


def sign(values):
    return hmac.new(SECRET.encode(), ";".join(values).encode(), hashlib.md5).hexdigest()


def callback(widget, status="Approved", **changes):
    payload = {
        "merchantAccount": widget["merchantAccount"],
        "orderReference": widget["orderReference"],
        "amount": widget["amount"],
        "currency": "UAH",
        "authCode": "123456",
        "cardPan": "411111****1111",
        "transactionStatus": status,
        "reasonCode": 1100,
        **changes,
    }
    payload["merchantSignature"] = sign(
        tuple(
            str(payload[k])
            for k in (
                "merchantAccount",
                "orderReference",
                "amount",
                "currency",
                "authCode",
                "cardPan",
                "transactionStatus",
                "reasonCode",
            )
        )
    )
    return payload


@pytest.fixture
async def merchant(app, monkeypatch):
    provider = await app.state.dishka_container.get(WayForPayProvider)
    monkeypatch.setattr(
        provider,
        "_config",
        WayForPayConfig(
            merchant_account="test-store",
            merchant_domain_name="example.com",
            secret_key=SECRET,
        ),
    )
    return provider


@pytest.fixture
async def payment(client, product, order_payload, idempotency_key, merchant):
    payload = order_payload(product.id, payment_method="card")
    headers = {"Idempotency-Key": idempotency_key}
    response = await client.post("/api/v1/orders", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json(), payload, headers


async def test_disabled_provider_is_explicit(
    client, product, order_payload, idempotency_key
):
    assert (await client.get("/api/v1/payments/availability")).json() == {
        "online_card_enabled": False,
        "test_mode": False,
    }
    response = await client.post(
        "/api/v1/orders",
        json=order_payload(product.id, payment_method="card"),
        headers={"Idempotency-Key": idempotency_key},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "payment_provider_unavailable"
    response = await client.post(
        "/api/v1/payments/wayforpay/callback",
        json=callback(
            {
                "merchantAccount": "test-store",
                "orderReference": "unknown",
                "amount": "1.00",
            }
        ),
    )
    assert response.status_code == 503


async def test_widget_is_signed_and_order_retry_reuses_session(client, payment):
    order, payload, headers = payment
    widget = order["payment_widget"]
    assert (await client.get("/api/v1/payments/availability")).json()[
        "online_card_enabled"
    ]
    assert (
        widget["serviceUrl"] == "https://example.com/api/v1/payments/wayforpay/callback"
    )
    values = (
        widget["merchantAccount"],
        widget["merchantDomainName"],
        widget["orderReference"],
        str(widget["orderDate"]),
        widget["amount"],
        widget["currency"],
        *widget["productName"],
        *(str(c) for c in widget["productCount"]),
        *widget["productPrice"],
    )
    assert widget["merchantSignature"] == sign(values)
    retry = (await client.post("/api/v1/orders", json=payload, headers=headers)).json()
    assert retry["id"] == order["id"]
    assert retry["payment_widget"] == widget
    assert SECRET not in str(order)


@pytest.mark.parametrize(
    "status, expected",
    [
        ("Approved", "paid"),
        ("Declined", "failed"),
        ("Expired", "failed"),
        ("Voided", "failed"),
        ("Pending", "pending"),
        ("WaitingAuthComplete", "pending"),
    ],
)
async def test_callback_updates_verified_status(client, payment, status, expected, uow):
    order, _, _ = payment
    response = await client.post(
        "/api/v1/payments/wayforpay/callback",
        json=callback(order["payment_widget"], status),
    )
    assert response.status_code == 200, response.text
    ack = response.json()
    assert ack["signature"] == sign((ack["orderReference"], "accept", str(ack["time"])))
    result = await client.get(
        f"/api/v1/payments/wayforpay/{order['payment_attempt_id']}"
    )
    assert result.json()["status"] == expected
    persisted = (
        await uow.session.execute(
            select(Order)
            .where(Order.id == UUID(order["id"]))
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert persisted.payment_status == expected


@pytest.mark.parametrize(
    "change, status",
    [
        ({"merchantAccount": "other-store"}, 401),
        ({"amount": "1.00"}, 409),
        ({"currency": "EUR"}, 409),
        ({"orderReference": "missing"}, 404),
    ],
)
async def test_callback_rejects_mismatched_payment(client, payment, change, status):
    response = await client.post(
        "/api/v1/payments/wayforpay/callback",
        json=callback(payment[0]["payment_widget"], **change),
    )
    assert response.status_code == status


@pytest.mark.parametrize("signature", ["0" * 32, "я" * 32])
async def test_invalid_signature_is_not_500(client, payment, signature):
    payload = callback(payment[0]["payment_widget"])
    payload["merchantSignature"] = signature
    response = await client.post("/api/v1/payments/wayforpay/callback", json=payload)
    assert response.status_code in {401, 422}


@pytest.mark.parametrize("body", [b"not json", b"\xff", b"{}", b"[]"])
async def test_malformed_callbacks(client, body):
    response = await client.post("/api/v1/payments/wayforpay/callback", content=body)
    assert response.status_code == 422


async def test_duplicate_and_late_callbacks_preserve_paid_order(client, payment):
    order, payload, headers = payment
    for status in ["Approved", "Approved", "Declined", "Pending"]:
        response = await client.post(
            "/api/v1/payments/wayforpay/callback",
            json=callback(order["payment_widget"], status),
        )
        assert response.status_code == 200
    retry = (await client.post("/api/v1/orders", json=payload, headers=headers)).json()
    assert retry["payment_status"] == "paid"
    assert retry["payment_widget"] is None


async def test_old_approval_and_new_decline_cannot_unpay_order(client, payment):
    order, payload, headers = payment
    await client.post(
        "/api/v1/payments/wayforpay/callback",
        json=callback(order["payment_widget"], "Declined"),
    )
    retry = (await client.post("/api/v1/orders", json=payload, headers=headers)).json()
    assert retry["payment_attempt_id"] != order["payment_attempt_id"]
    assert retry["payment_status"] == "pending"
    latest_attempt_id = retry["payment_attempt_id"]
    for widget, status in [
        (order["payment_widget"], "Approved"),
        (retry["payment_widget"], "Declined"),
    ]:
        assert (
            await client.post(
                "/api/v1/payments/wayforpay/callback", json=callback(widget, status)
            )
        ).status_code == 200
    retry = (await client.post("/api/v1/orders", json=payload, headers=headers)).json()
    assert retry["payment_status"] == "paid"
    assert retry["payment_widget"] is None
    assert (await client.get(f"/api/v1/payments/wayforpay/{latest_attempt_id}")).json()[
        "status"
    ] == "paid"


async def test_status_not_found_and_validation(client):
    assert (
        await client.get(f"/api/v1/payments/wayforpay/{uuid4()}")
    ).status_code == 404
    assert (
        await client.get("/api/v1/payments/wayforpay/not-a-uuid")
    ).status_code == 422


async def test_full_refund_is_terminal_and_cannot_be_recharged(client, payment):
    order, payload, headers = payment
    for status in ["Approved", "Refunded", "Refunded", "Approved", "Declined"]:
        response = await client.post(
            "/api/v1/payments/wayforpay/callback",
            json=callback(order["payment_widget"], status),
        )
        assert response.status_code == 200
    retry = (await client.post("/api/v1/orders", json=payload, headers=headers)).json()
    assert retry["payment_status"] == "refunded"
    assert retry["payment_widget"] is None


async def test_discounted_payment_lines_match_the_total(merchant):
    from decimal import Decimal
    from types import SimpleNamespace

    order = SimpleNamespace(
        discount=Decimal("10"),
        total=Decimal("182.00"),
        number="test",
        items=[SimpleNamespace(quantity=2)],
    )
    names, prices, counts = merchant._product_lines(order)
    assert len(names) == len(prices) == len(counts) == 1
    assert (
        sum(Decimal(p) * c for p, c in zip(prices, counts, strict=True)) == order.total
    )


async def test_card_requires_first_and_last_name(
    client, product, merchant, order_payload, idempotency_key
):
    response = await client.post(
        "/api/v1/orders",
        json=order_payload(product.id, payment_method="card", customer_name="Олена"),
        headers={"Idempotency-Key": idempotency_key},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "payment_customer_name_required"


@pytest.mark.parametrize(
    "account, test_mode", [("test_merch_n1", False), ("live-store", True), (None, True)]
)
async def test_mode_rejects_misleading_configuration(account, test_mode):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        WayForPayConfig(
            merchant_account=account,
            merchant_domain_name="example.com" if account else None,
            secret_key=SECRET if account else None,
            test_mode=test_mode,
        )


async def test_sandbox_order_is_marked_and_contacts_are_anonymous(
    client, merchant, monkeypatch, product, order_payload, idempotency_key, uow
):
    from datetime import UTC, datetime, timedelta

    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    before = await uow.dashboard.get_stats(today, week_ago)
    monkeypatch.setattr(
        merchant,
        "_config",
        WayForPayConfig(
            merchant_account="test_merch_n1",
            merchant_domain_name="example.com",
            secret_key=SECRET,
            test_mode=True,
        ),
    )
    availability = (await client.get("/api/v1/payments/availability")).json()
    assert availability == {"online_card_enabled": True, "test_mode": True}
    request = order_payload(product.id, payment_method="card")
    headers = {"Idempotency-Key": idempotency_key}
    response = await client.post("/api/v1/orders", json=request, headers=headers)
    assert response.status_code == 201, response.text
    order = response.json()
    assert order["payment_is_test"] is True
    assert await uow.dashboard.get_stats(today, week_ago) == before
    widget = order["payment_widget"]
    assert widget["clientEmail"] == "test@example.invalid"
    assert widget["clientPhone"] != request["phone"].lstrip("+")
    assert (
        await client.post("/api/v1/payments/wayforpay/callback", json=callback(widget))
    ).status_code == 200
    result = (
        await client.get(f"/api/v1/payments/wayforpay/{order['payment_attempt_id']}")
    ).json()
    assert result["status"] == "paid" and result["is_test"] is True
    retry = (await client.post("/api/v1/orders", json=request, headers=headers)).json()
    assert retry["payment_is_test"] is True and retry["payment_widget"] is None


async def test_test_credentials_cannot_change_live_order(
    client, payment, merchant, monkeypatch
):
    order, request, headers = payment
    monkeypatch.setattr(
        merchant,
        "_config",
        WayForPayConfig(
            merchant_account="test_merch_n1",
            merchant_domain_name="example.com",
            secret_key=SECRET,
            test_mode=True,
        ),
    )
    payload = callback(order["payment_widget"], merchantAccount="test_merch_n1")
    assert (
        await client.post("/api/v1/payments/wayforpay/callback", json=payload)
    ).status_code == 409
    result = await client.post("/api/v1/orders", json=request, headers=headers)
    assert result.status_code == 409
    assert result.json()["code"] == "payment_mode_changed"
