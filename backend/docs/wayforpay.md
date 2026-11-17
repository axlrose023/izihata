# WayForPay

Card checkout uses the hosted WayForPay widget; card details never reach this API.
The backend calculates and signs the persisted order total. Configure all three
`APP__WAYFORPAY__MERCHANT_ACCOUNT`, `MERCHANT_DOMAIN_NAME`, `SECRET_KEY` settings
to enable it. Keep production credentials in the server environment only.
Without credentials the UI disables online card payment and the API rejects it.
Cash on delivery and company invoices remain independent of WayForPay.

- `GET /api/v1/payments/availability`: public checkout capabilities.
- `POST /api/v1/payments/wayforpay/callback`: signed server notification, no session
  or browser CSRF requirement. The signed acknowledgment follows the DB commit.
- `GET /api/v1/payments/wayforpay/{attempt_id}`: rate-limited order payment status;
  the unpredictable UUID acts as a guest capability. No contact/card data is returned.

Callbacks check merchant, HMAC, reference, amount and currency. All attempts for
one order share its DB row lock; duplicates and late failures cannot undo payment.
Retries reuse a pending reference; only failed attempts receive a new reference.
Full-refund notifications are reflected, but refund initiation is not exposed.
Paid/refunded orders never issue another payment session on retry.

Widget callbacks are UI hints, not proof of payment. Closing/failing the widget
keeps the basket; pending results use bounded polling on the result page. The
provider retries notifications, so no additional Taskiq polling job is introduced.

Before enabling production, apply migrations, configure an activated merchant,
verify the public HTTPS callback URL and test provider delivery to it. Never put
the public test merchant credentials into a live shop: their secret is public.
Development demos can explicitly enable `APP__WAYFORPAY__TEST_MODE=true` with
the official `test_merch_n1` account. This marks orders persistently, anonymizes
contacts sent to WayForPay and prevents test callbacks from changing live orders.
Switching back to live credentials requires `TEST_MODE=false`; existing test
orders retain their label and cannot be reissued under live credentials.

References: https://wiki.wayforpay.com/view/852091 and
https://wiki.wayforpay.com/view/852102.
