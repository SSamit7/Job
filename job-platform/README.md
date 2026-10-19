# Job Platform (Django)

A job posting & hiring platform where clients post jobs, workers apply,
the client selects a worker (creating a Contract), and on completion
payment is split 90% worker / 10% platform commission - paid via real
eSewa/Khalti gateway integrations (sandbox by default) or manual bank
transfer.

## Setup
```
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## App responsibilities
- accounts       -> CustomUser, ClientProfile, WorkerProfile, WorkerAvailability, auth
- jobs           -> Job model (incl. location/schedule), posting, browsing/search, SavedJob
- applications   -> Worker applications to jobs (gated by wallet balance)
- contracts      -> Created when client selects a worker
- payments       -> Job payments + wallet top-ups via real eSewa/Khalti gateways,
                     10% commission split, PlatformWallet (admin's commission balance
                     + receiving account/QR), WorkerWallet
- reviews        -> Ratings after contract completion
- core           -> Home, about, contact, dashboards
- notifications  -> In-app bell + best-effort email on job posted / application
                     received / selected / payment success / wallet top-up
- messaging      -> Chat between client and worker, unlocked once a contract's
                     payment succeeds

## Going live with real eSewa/Khalti payments
By default this runs against eSewa's and Khalti's **sandbox** environments -
genuinely working, cryptographically verified, but no real money moves.
To accept real payments:

1. **eSewa**: sign up as a merchant at https://merchant.esewa.com.np (requires
   business KYC) to get your own merchant code + secret key. Set these in `.env`:
   `ESEWA_MERCHANT_CODE`, `ESEWA_SECRET_KEY`, and switch
   `ESEWA_PAYMENT_URL` / `ESEWA_STATUS_CHECK_URL` from the `rc-epay`/`uat` hosts
   to the production `epay.esewa.com.np` hosts (see comments in `config/settings.py`).
2. **Khalti**: sign up at https://merchant.khalti.com for a live secret key and
   set `KHALTI_SECRET_KEY` (swap `KHALTI_INITIATE_URL`/`KHALTI_LOOKUP_URL` from
   `dev.khalti.com` to Khalti's production API host).
3. Set `SITE_BASE_URL` to your real public HTTPS domain - both gateways redirect
   the user's browser back there after payment.
4. Set `DEBUG=False` and configure `ALLOWED_HOSTS` for your real domain.
5. Run `python manage.py check` - a system check (`apps/payments/checks.py`)
   will loudly warn if production mode is still pointed at sandbox credentials,
   an unconfigured Khalti key, or a localhost `SITE_BASE_URL`. The same warnings
   also show on the in-app Platform Wallet page (staff only).

Bank Transfer needs no gateway signup - just fill in your real account details
and (optionally) upload your real payment QR code image in Django admin under
**Payments > Platform wallet**.
