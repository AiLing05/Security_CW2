import os
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import re
from django.utils.translation import gettext as _

phone_validator = RegexValidator(
    regex=r'^\d{10}$',
    message='Contact number must be exactly 10 digits.'
)
