from django.shortcuts import render, redirect
from django.views import View
from django.views.generic.edit import FormView
from django.contrib.auth import login, authenticate

from core.forms import RegistrationForm, AccountUpdateForm, BookingForm
from core.models import Table


class HomePage(View):
    """
    Responsible for the internal logic of main page formation
    """
    template_name = 'core/index.html'

    def get(self, request):
        tables = Table.objects.values_list('pk', flat=True)
        return render(request, self.template_name, context={'tables': tables})


class TableView(View):
    template_name = 'core/table.html'

    def get(self, request, table_id):
        context = {}

        table = Table.objects.get(pk=table_id)
        table.description = table.description.split('\n')

        context['table'] = table
        return render(request, self.template_name, context)


class BookingView(FormView):
    template_name = 'core/table_booking.html'

    def post(self, request, *args, **kwargs):
        context = {}
        form = BookingForm(request.POST)

        # Point of entry to the shit
        # https://stackoverflow.com/questions/44717442/this-querydict-instance-is-immutable
        default_mutability = form.data._mutable
        form.data._mutable = True

        form.data['table'] = request.resolver_match.kwargs['table_id']
        form.data['account'] = request.user.pk

        form.data._mutable = default_mutability
        # Point of exit from the shit

        if form.is_valid():
            form.save()
            return redirect('homePage')
        else:
            context['form'] = form
            return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        context = {}
        table = Table.objects.get(pk=request.resolver_match.kwargs['table_id'])
        form = BookingForm(custom_values={'max_capacity': table.capacity})
        context['form'] = form
        context['table'] = table
        return render(request, self.template_name, context)


class RegisterFormView(FormView):
    """
    Responsible for the internal logic of the registration page formation.
    """
    template_name = 'registration/register.html'

    def post(self, request, *args, **kwargs):
        context = {}
        form = RegistrationForm(request.POST)
        if form.is_valid() and request.recaptcha_is_valid:
            form.save()
            email = form.cleaned_data.get('email')
            raw_password = form.cleaned_data.get('password1')
            account = authenticate(email=email, password=raw_password)
            login(request, account)
            return redirect('homePage')
        else:
            context['form'] = form
            return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        context = {}
        form = RegistrationForm()
        context['form'] = form
        return render(request, self.template_name, context)


class AccountDetails(FormView):
    """
    Responsible for the internal logic of account details page formation.
    """
    template_name = 'core/account_details.html'

    def post(self, request, *args, **kwargs):
        """
        Using for updating account info

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        context = {}
        form = AccountUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            form.initial = {
                'email': request.POST['email'],
                'username': request.POST['username']
            }

            context['success_message'] = 'Updated'

        context['account_form'] = form
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        context = {}
        form = AccountUpdateForm(
            initial={
                'email': request.user.email,
                'username': request.user.username,
            }
        )

        context['account_form'] = form
        return render(request, self.template_name, context)


class PageNotFound(View):
    """
    Responsible for the logic of forming the page to which the user gets the wrong url link.
    """
    template_name = 'core/not_found.html'

    def get(self, request):
        return render(request, self.template_name, context={})
