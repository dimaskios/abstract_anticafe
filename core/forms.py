from datetimerange import DateTimeRange

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate

from datetime import datetime, timedelta
from pytz import timezone

from abstract_anticafe.settings import TIME_ZONE
from core.models import Account, TableBookingQueue


MAX_CAPACITY = 8
MAX_BOOKING_DURATION = 3  # hours


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(max_length=60, help_text='Required. Add a valid email address')

    class Meta:
        model = Account
        fields = ("email", "username", "password1", "password2")


class AccountAuthenticationForm(forms.ModelForm):
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

    class Meta:
        model = Account
        fields = ('email', 'password')

    def clean(self):
        if self.is_valid():
            email = self.cleaned_data['email']
            password = self.cleaned_data['password']
            if not authenticate(email=email, password=password):
                raise forms.ValidationError('Invalid login or password')


class AccountUpdateForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ('email', 'username')

    def clean_email(self):
        email = self.cleaned_data['email']

        if Account.objects.exclude(pk=self.instance.pk).filter(email=email):
            raise forms.ValidationError(f'Email {email} already exist')
        else:
            return email

    def clean_username(self):
        username = self.cleaned_data['username']

        if Account.objects.exclude(pk=self.instance.pk).filter(username=username):
            raise forms.ValidationError(f'Username {username} already exist')
        else:
            return username


class BookingForm(forms.ModelForm):
    class Meta:
        model = TableBookingQueue
        fields = ('table', 'account', 'guests_count', 'dt_start', 'dt_end')
        widgets = {
            'table': forms.HiddenInput(),
            'account': forms.HiddenInput(),
        }

    def start_end_excetion(self, msg):
        """
        The main method to raise validation errors in fields dt_start, dt_end

        :param msg: string Error text
        :return: None
        """
        self.add_error('dt_start', forms.ValidationError(msg))
        self.add_error('dt_end', forms.ValidationError(msg))

    def __init__(self, *args, **kwargs):
        custom_values = kwargs.pop('custom_values', {})

        super().__init__(*args, **kwargs)

        # ----------------------field for guests count--------------------------------------
        attributes = {
            'autocomplete': 'off',
            'class': 'form-control mb-3',
        }

        self.fields['guests_count'] = forms.IntegerField(min_value=1,
                                                         max_value=custom_values.get('max_capacity', MAX_CAPACITY),
                                                         widget=forms.NumberInput(attrs=attributes))
        self.fields['guests_count'].label = 'Number of guests'
        # ----------------------------------------------------------------------------------

        # --------------  field for datetime of booking start ------------------------------
        attributes = {
            'autocomplete': 'off',
            'class': 'dt_start form-control mb-3',
            'readonly': None,
        }

        self.fields['dt_start'] = forms.DateTimeField(input_formats=['%d/%m/%Y %H:%M'],
                                                      widget=forms.TextInput(attrs=attributes))
        self.fields['dt_start'].label = 'Booking start date and time'
        # ----------------------------------------------------------------------------------

        # --------------  field for datetime of booking end   ------------------------------
        attributes = {
            'autocomplete': 'off',
            'class': 'dt_end form-control mb-3',
            'readonly': None,
        }

        self.fields['dt_end'] = forms.DateTimeField(input_formats=['%d/%m/%Y %H:%M'],
                                                    widget=forms.TextInput(attrs=attributes))
        self.fields['dt_end'].label = 'Booking end date and time'
        # ----------------------------------------------------------------------------------

    def clean(self):
        """
        Custom validation of fields
        Ex.: dt_start must be lower than a dt_end
        :return:
        """
        cleaned_data = super().clean()
        dt_start = cleaned_data.get('dt_start')
        dt_end = cleaned_data.get('dt_end')

        if dt_start >= dt_end:
            self.start_end_excetion(msg='The start date and time of the reservation\
                                         must be less than the end date and time.')
            return
        elif dt_start < datetime.now(tz=timezone(TIME_ZONE)):
            self.start_end_excetion(msg='The start time cannot be less than the current time.')
            return
        elif dt_end - dt_start > timedelta(hours=MAX_BOOKING_DURATION):
            self.start_end_excetion(msg=f'You can\'t book for more than {MAX_BOOKING_DURATION} hours')
            return

        booking_datetime_range = DateTimeRange(dt_start, dt_end)

        reservations = TableBookingQueue.objects.filter(table=cleaned_data.get('table'))

        for busy_table in reservations:
            busy_table_datetime_range = DateTimeRange(busy_table.dt_start, busy_table.dt_end)

            if booking_datetime_range.is_intersection(busy_table_datetime_range):
                self.start_end_excetion(msg='This range is already booked :3')
                break
