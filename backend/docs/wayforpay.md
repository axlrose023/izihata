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
  the unpredictable UUID acts as a guest capability for the current invoice link.
  No contact/card data is returned, and the response is not cacheable.

Callbacks check merchant, HMAC, reference, amount and currency. All attempts for
one order share its DB row lock; duplicates and late failures cannot undo payment.
Checkout creates a provider invoice and saves its URL with the payment attempt;
closing and reopening the widget reuses that invoice without placing another order.
The invoice expires after 24 hours. Older attempts without an invoice and expired
invoices require manager assistance instead of silently creating another payment.
Full-refund notifications are reflected, but refund initiation is not exposed.
Paid/refunded orders never issue another payment session on retry.

Widget callbacks are UI hints, not proof of payment. Closing/failing the widget
opens the saved order page, where the invoice can be reopened. Pending results
use bounded polling on the result page. The
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
