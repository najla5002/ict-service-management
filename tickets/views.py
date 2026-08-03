from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from .models import Ticket, Comment, MaintenanceLog, Profile, Notification
from .forms import RegisterForm, TicketForm, CommentForm, MaintenanceLogForm


# ─── AUTH VIEWS ───────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password!')
    else:
        form = AuthenticationForm()
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('login')


# ─── DASHBOARD ────────────────────────────────────────────

@login_required
def dashboard(request):
    user = request.user
    try:
        role = user.profile.role
    except:
        role = 'user'

    if role == 'admin' or user.is_superuser:
        tickets = Ticket.objects.all()
    elif role == 'technician':
        tickets = Ticket.objects.filter(assigned_to=user)
    else:
        tickets = Ticket.objects.filter(created_by=user)

    unread_notifications = Notification.objects.filter(
        user=user, is_read=False).count()

    context = {
        'tickets': tickets,
        'total': tickets.count(),
        'pending': tickets.filter(status='pending').count(),
        'in_progress': tickets.filter(status='in_progress').count(),
        'resolved': tickets.filter(status='resolved').count(),
        'role': role,
        'unread_notifications': unread_notifications,
        'critical_tickets': tickets.filter(priority='critical', status__in=['pending', 'in_progress']).count(),
        'high_tickets': tickets.filter(priority='high', status__in=['pending', 'in_progress']).count(),
    }
    return render(request, 'tickets/dashboard.html', context)

# ─── TICKET VIEWS ─────────────────────────────────────────

@login_required
def ticket_list(request):
    try:
        role = request.user.profile.role
    except:
        role = 'user'

    if role in ['admin', 'technician'] or request.user.is_superuser:
        tickets = Ticket.objects.all()
    else:
        tickets = Ticket.objects.filter(created_by=request.user)

    search = request.GET.get('search', '')
    if search:
        tickets = tickets.filter(title__icontains=search)

    status = request.GET.get('status', '')
    if status:
        tickets = tickets.filter(status=status)

    category = request.GET.get('category', '')
    if category:
        tickets = tickets.filter(category=category)

    priority = request.GET.get('priority', '')
    if priority:
        tickets = tickets.filter(priority=priority)

    context = {
        'tickets': tickets,
        'role': role,
        'search': search,
        'selected_status': status,
        'selected_category': category,
        'selected_priority': priority,
    }
    return render(request, 'tickets/ticket_list.html', context)


@login_required
def ticket_create(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.save()
            messages.success(request, 'Ticket submitted successfully!')
            return redirect('ticket_list')
    else:
        form = TicketForm()
    return render(request, 'tickets/ticket_form.html', {'form': form, 'title': 'Submit New Ticket'})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    comments = ticket.comments.all()
    logs = ticket.logs.all()
    comment_form = CommentForm()
    log_form = MaintenanceLogForm()

    if request.method == 'POST':
        if 'comment_submit' in request.POST:
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.ticket = ticket
                comment.author = request.user
                comment.save()
                messages.success(request, 'Comment added!')
                return redirect('ticket_detail', pk=pk)

        elif 'log_submit' in request.POST:
            log_form = MaintenanceLogForm(request.POST)
            if log_form.is_valid():
                log = log_form.save(commit=False)
                log.ticket = ticket
                log.technician = request.user
                log.save()
                messages.success(request, 'Maintenance log added!')
                return redirect('ticket_detail', pk=pk)

        elif 'close_ticket' in request.POST:
            ticket.status = 'closed'
            ticket.save()
            Notification.objects.create(
                user=ticket.created_by,
                message=f'Your Ticket #{ticket.id}: "{ticket.title}" has been closed.'
            )
            messages.success(request, 'Ticket closed successfully!')
            return redirect('ticket_detail', pk=pk)

        elif 'reopen_ticket' in request.POST:
            ticket.status = 'in_progress'
            ticket.save()
            Notification.objects.create(
                user=ticket.created_by,
                message=f'Your Ticket #{ticket.id}: "{ticket.title}" has been reopened.'
            )
            messages.success(request, 'Ticket reopened successfully!')
            return redirect('ticket_detail', pk=pk)

    context = {
        'ticket': ticket,
        'comments': comments,
        'logs': logs,
        'comment_form': comment_form,
        'log_form': log_form,
    }
    return render(request, 'tickets/ticket_detail.html', context)


@login_required
def ticket_update(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    try:
        role = request.user.profile.role
    except:
        role = 'user'

    if request.method == 'POST':
        status = request.POST.get('status')
        assigned_to_id = request.POST.get('assigned_to')
        old_assigned = ticket.assigned_to
        old_status = ticket.status

        if status:
            ticket.status = status

        if assigned_to_id:
            if assigned_to_id == 'none':
                ticket.assigned_to = None
            else:
                new_technician = get_object_or_404(User, pk=assigned_to_id)
                ticket.assigned_to = new_technician

                if old_assigned != new_technician:
                    Notification.objects.create(
                        user=new_technician,
                        message=f'You have been assigned Ticket #{ticket.id}: "{ticket.title}" - Priority: {ticket.get_priority_display()}'
                    )

        if status and status != old_status:
            Notification.objects.create(
                user=ticket.created_by,
                message=f'Your Ticket #{ticket.id}: "{ticket.title}" status changed to {ticket.get_status_display()}'
            )

        ticket.save()
        messages.success(request, 'Ticket updated successfully!')
        return redirect('ticket_detail', pk=pk)

    technicians = User.objects.filter(profile__role='technician')
    return render(request, 'tickets/ticket_update.html', {
        'ticket': ticket,
        'technicians': technicians,
        'role': role,
    })


# ─── REPORTS ──────────────────────────────────────────────

@login_required
def reports(request):
    try:
        role = request.user.profile.role
    except:
        role = 'user'

    all_tickets = Ticket.objects.all()

    context = {
        'role': role,
        'total': all_tickets.count(),
        'pending': all_tickets.filter(status='pending').count(),
        'in_progress': all_tickets.filter(status='in_progress').count(),
        'resolved': all_tickets.filter(status='resolved').count(),
        'closed': all_tickets.filter(status='closed').count(),
        'network': all_tickets.filter(category='network').count(),
        'hardware': all_tickets.filter(category='hardware').count(),
        'ups': all_tickets.filter(category='ups').count(),
        'software': all_tickets.filter(category='software').count(),
        'account': all_tickets.filter(category='account').count(),
        'other': all_tickets.filter(category='other').count(),
        'low': all_tickets.filter(priority='low').count(),
        'medium': all_tickets.filter(priority='medium').count(),
        'high': all_tickets.filter(priority='high').count(),
        'critical': all_tickets.filter(priority='critical').count(),
    }
    return render(request, 'tickets/reports.html', context)


# ─── PROFILE ──────────────────────────────────────────────

@login_required
def profile(request):
    try:
        user_profile = request.user.profile
    except:
        user_profile = Profile.objects.create(user=request.user, role='user')

    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
        user_profile.phone = request.POST.get('phone', '')
        user_profile.department = request.POST.get('department', '')
        user_profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')

    tickets = Ticket.objects.filter(created_by=request.user)
    context = {
        'user_profile': user_profile,
        'total': tickets.count(),
        'pending': tickets.filter(status='pending').count(),
        'in_progress': tickets.filter(status='in_progress').count(),
        'resolved': tickets.filter(status='resolved').count(),
    }
    return render(request, 'tickets/profile.html', context)


# ─── NOTIFICATIONS ────────────────────────────────────────

@login_required
def notifications(request):
    notifs = Notification.objects.filter(user=request.user)
    unread = notifs.filter(is_read=False)
    unread.update(is_read=True)
    return render(request, 'tickets/notifications.html', {'notifications': notifs})


# ─── PDF EXPORT ───────────────────────────────────────────

@login_required
def export_tickets_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="tickets_report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    title = Paragraph("ICT Service Management System - Tickets Report", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 20))

    try:
        role = request.user.profile.role
    except:
        role = 'user'

    if role in ['admin', 'technician'] or request.user.is_superuser:
        tickets = Ticket.objects.all()
    else:
        tickets = Ticket.objects.filter(created_by=request.user)

    data = [['#', 'Title', 'Category', 'Priority', 'Status', 'Created By', 'Date']]

    for ticket in tickets:
        data.append([
            f'#{ticket.id}',
            ticket.title[:30],
            ticket.get_category_display(),
            ticket.get_priority_display(),
            ticket.get_status_display(),
            ticket.created_by.username,
            ticket.created_at.strftime('%d %b %Y'),
        ])

    table = Table(data, colWidths=[40, 140, 100, 70, 80, 80, 70])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565c0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4ff')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWHEIGHT', (0, 0), (-1, -1), 25),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    summary = Paragraph(f"Total Tickets: {tickets.count()} | Generated by: {request.user.username}", styles['Normal'])
    elements.append(summary)

    doc.build(elements)
    return response


# ─── USER MANAGEMENT ──────────────────────────────────────

@login_required
def user_list(request):
    try:
        role = request.user.profile.role
    except:
        role = 'user'

    if role != 'admin' and not request.user.is_superuser:
        messages.error(request, 'Access denied!')
        return redirect('dashboard')

    users = User.objects.all().order_by('username')

    search = request.GET.get('search', '')
    if search:
        users = users.filter(
            username__icontains=search
        ) | User.objects.filter(
            first_name__icontains=search
        ) | User.objects.filter(
            last_name__icontains=search
        ) | User.objects.filter(
            email__icontains=search
        )
        users = users.distinct()

    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(profile__role=role_filter)

    return render(request, 'tickets/user_list.html', {
        'users': users,
        'search': search,
        'selected_role': role_filter,
    })


@login_required
def user_create(request):
    try:
        role = request.user.profile.role
    except:
        role = 'user'

    if role != 'admin' and not request.user.is_superuser:
        messages.error(request, 'Access denied!')
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            try:
                user.profile.role = request.POST.get('role', 'user')
                user.profile.save()
            except:
                pass
            messages.success(request, f'User {user.username} created successfully!')
            return redirect('user_list')
    else:
        form = RegisterForm()

    return render(request, 'tickets/user_create.html', {'form': form})


@login_required
def user_edit(request, pk):
    try:
        role = request.user.profile.role
    except:
        role = 'user'

    if role != 'admin' and not request.user.is_superuser:
        messages.error(request, 'Access denied!')
        return redirect('dashboard')

    edit_user = get_object_or_404(User, pk=pk)
    try:
        edit_profile = edit_user.profile
    except:
        edit_profile = Profile.objects.create(user=edit_user, role='user')

    if request.method == 'POST':
        edit_user.first_name = request.POST.get('first_name', '')
        edit_user.last_name = request.POST.get('last_name', '')
        edit_user.email = request.POST.get('email', '')
        edit_user.is_active = request.POST.get('is_active') == 'on'
        edit_user.save()
        edit_profile.role = request.POST.get('role', 'user')
        edit_profile.phone = request.POST.get('phone', '')
        edit_profile.department = request.POST.get('department', '')
        edit_profile.save()
        messages.success(request, f'User {edit_user.username} updated successfully!')
        return redirect('user_list')

    return render(request, 'tickets/user_edit.html', {
        'edit_user': edit_user,
        'edit_profile': edit_profile,
    })


@login_required
def user_delete(request, pk):
    try:
        role = request.user.profile.role
    except:
        role = 'user'

    if role != 'admin' and not request.user.is_superuser:
        messages.error(request, 'Access denied!')
        return redirect('dashboard')

    delete_user = get_object_or_404(User, pk=pk)
    if delete_user != request.user:
        delete_user.delete()
        messages.success(request, 'User deleted successfully!')
    else:
        messages.error(request, 'You cannot delete yourself!')
    return redirect('user_list')


# ─── FAQ / HELP ───────────────────────────────────────────

@login_required
def faq(request):
    return render(request, 'tickets/faq.html')


# ─── CHANGE PASSWORD ──────────────────────────────────────

@login_required
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        if not request.user.check_password(old_password):
            messages.error(request, 'Current password is incorrect!')
        elif new_password1 != new_password2:
            messages.error(request, 'New passwords do not match!')
        elif len(new_password1) < 8:
            messages.error(request, 'Password must be at least 8 characters!')
        else:
            request.user.set_password(new_password1)
            request.user.save()
            messages.success(request, 'Password changed successfully! Please login again.')
            return redirect('login')

    return render(request, 'tickets/change_password.html')


# ─── USER STATISTICS ──────────────────────────────────────

@login_required
def user_statistics(request):
    try:
        role = request.user.profile.role
    except:
        role = 'user'

    if role != 'admin' and not request.user.is_superuser:
        messages.error(request, 'Access denied!')
        return redirect('dashboard')

    users = User.objects.all()
    user_stats = []

    for u in users:
        tickets = Ticket.objects.filter(created_by=u)
        user_stats.append({
            'user': u,
            'total': tickets.count(),
            'pending': tickets.filter(status='pending').count(),
            'in_progress': tickets.filter(status='in_progress').count(),
            'resolved': tickets.filter(status='resolved').count(),
            'closed': tickets.filter(status='closed').count(),
        })

    user_stats = sorted(user_stats, key=lambda x: x['total'], reverse=True)

    return render(request, 'tickets/user_statistics.html', {
        'user_stats': user_stats,
    })