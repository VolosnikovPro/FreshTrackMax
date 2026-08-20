# Headcount model is defined in app/models/consumption.py
# This file exists so imports like `from app.models import headcount` work
from app.models.consumption import DailyHeadcount as Headcount

__all__ = ["Headcount"]
