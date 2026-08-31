# Job Platform (Django)

A job posting & hiring platform where clients post jobs, workers apply,
the client selects a worker (creating a Contract), and on completion
payment is split 90% worker / 10% platform commission.

## Setup
```
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## App responsibilities
- accounts      -> CustomUser, ClientProfile, WorkerProfile, auth
- jobs          -> Job model, posting, browsing/search
- applications  -> Worker applications to jobs
- contracts     -> Created when client selects a worker
- payments      -> Payment + 10% commission split logic
- reviews       -> Ratings after contract completion
- core          -> Home, about, contact, dashboards
