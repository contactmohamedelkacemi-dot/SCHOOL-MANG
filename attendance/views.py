from django.shortcuts import render, redirect, get_object_or_404
from .models import Attendance, AttendanceSession, Justification, JustificationSession
from classes.models import Group
from school_management.decorators import admin_required, teacher_required
from django.contrib import messages
from datetime import date
from .forms import JustificationForm, StudentJustificationForm
from django.contrib.auth.decorators import login_required


@admin_required
def group_select(request):
    groups = Group.objects.select_related("class_assigned").all()
    return render(request, "attendance/group_select.html", {"groups": groups})


@admin_required
def group_attendance(request, group_id):
    group = get_object_or_404(Group.objects.prefetch_related("students"), pk=group_id)
    students = group.students.all().order_by("full_name")

    attendance_date = request.GET.get("date") or date.today().isoformat()

    # Pre-fetch all sessions for this group/date
    sessions = AttendanceSession.objects.filter(
        group=group, date=attendance_date
    ).select_related("student")

    # Pre-fetch justifications for these students on this date
    justifications = Justification.objects.prefetch_related("session_links").filter(
        student__in=students, date=attendance_date
    )

    student_sessions = {}
    for s in sessions:
        if s.student_id not in student_sessions:
            student_sessions[s.student_id] = {}
        student_sessions[s.student_id][s.session_number] = s.status

    student_justifs = {j.student_id: j for j in justifications}

    student_records = []
    for student in students:
        s_sessions = student_sessions.get(student.id, {})

        # Calculate daily status (Absent > Late > Present)
        status_vals = list(s_sessions.values())
        if not status_vals:
            daily_status = None
        elif "Absent" in status_vals:
            daily_status = "Absent"
        elif "Late" in status_vals:
            daily_status = "Late"
        else:
            daily_status = "Present"

        justif = student_justifs.get(student.id)
        justif_status = None
        justif_sessions = []
        if justif:
            justif_status = justif.status  # Pending, Approved, Rejected
            justif_sessions = [js.session_number for js in justif.session_links.all()]

        if daily_status == "Absent" and not justif:
            justif_status = "Non justifié"

        student_records.append(
            {
                "student": student,
                "daily_status": daily_status,
                "sessions": s_sessions,
                "justification": justif,
                "justification_status": justif_status,
                "justified_sessions": justif_sessions,
            }
        )

    return render(
        request,
        "attendance/group_attendance.html",
        {
            "group": group,
            "student_records": student_records,
            "attendance_date": attendance_date,
        },
    )


from django.core.exceptions import PermissionDenied


@teacher_required
def teacher_group_select(request):
    try:
        teacher = request.user.teacher
        groups = (
            Group.objects.filter(teachers=teacher)
            .select_related("class_assigned")
            .distinct()
        )
    except Exception:
        groups = []
    return render(request, "attendance/teacher_group_select.html", {"groups": groups})


from schedule.models import GroupSchedule


@teacher_required
def teacher_group_attendance(request, group_id):
    group = get_object_or_404(
        Group.objects.prefetch_related("students", "teachers"), pk=group_id
    )

    # 1. Strict validation: Ensure the teacher exists and is assigned to this group
    try:
        teacher = request.user.teacher
    except Exception:
        messages.error(request, "Teacher profile not found.")
        return redirect("dashboard:teacher_dashboard")

    if teacher not in group.teachers.all():
        messages.error(
            request, "You are not authorized to take attendance for this group."
        )
        return redirect("dashboard:teacher_dashboard")

    # Extract date and session
    attendance_date = request.GET.get("date") or date.today().isoformat()

    # Pre-calculate allowed sessions for the selected day
    try:
        date_obj = date.fromisoformat(attendance_date)
        day_name = date_obj.strftime("%A")
    except ValueError:
        messages.error(request, "Invalid date format.")
        return redirect("dashboard:teacher_dashboard")

    allowed_schedules = GroupSchedule.objects.filter(
        teacher=teacher, group=group, day=day_name
    ).values_list("session_number", flat=True)
    allowed_sessions = list(allowed_schedules)

    # Attempt to get session number from GET, fallback to first allowed session if any
    try:
        session_number = int(
            request.GET.get("session", allowed_sessions[0] if allowed_sessions else 1)
        )
    except ValueError:
        session_number = allowed_sessions[0] if allowed_sessions else 1

    if request.method == "POST":
        post_date = request.POST.get("attendance_date")
        post_session = int(request.POST.get("session_number"))

        # Validate POST parameters to prevent tampering
        try:
            post_date_obj = date.fromisoformat(post_date)
            post_day_name = post_date_obj.strftime("%A")
        except ValueError:
            messages.error(request, "Invalid POST date format.")
            return redirect("dashboard:teacher_dashboard")

        if not GroupSchedule.objects.filter(
            teacher=teacher, group=group, day=post_day_name, session_number=post_session
        ).exists():
            messages.error(request, "You are not assigned to this session.")
            return redirect("dashboard:teacher_dashboard")

        students = group.students.all().order_by("full_name")
        student_ids = set(student.id for student in students)

        from .utils import update_student_risk

        for student in students:
            status = request.POST.get(f"status_{student.id}")
            if status and student.id in student_ids:
                AttendanceSession.objects.update_or_create(
                    student=student,
                    date=post_date,
                    session_number=post_session,
                    defaults={"group": group, "status": status},
                )
                update_student_risk(student)
        messages.success(
            request, f"Attendance saved for Session {post_session} on {post_date}"
        )
        return redirect(f"{request.path}?date={post_date}&session={post_session}")

    # GET Request Validation
    # Allow rendering if they simply don't have sessions (so the template can say "No sessions today")
    # But if they try to FORCE a session they don't own in the URL, block them
    if session_number not in allowed_sessions and allowed_sessions:
        messages.error(request, "You are not assigned to this session.")
        return redirect("dashboard:teacher_dashboard")

    # If no sessions allowed, we'll still render the page but the template will hide the table

    students = group.students.all().order_by("full_name")
    existing_sessions = AttendanceSession.objects.filter(
        group=group, date=attendance_date, session_number=session_number
    )
    session_map = {s.student_id: s.status for s in existing_sessions}

    student_records = []
    for student in students:
        student_records.append(
            {"student": student, "status": session_map.get(student.id)}
        )

    return render(
        request,
        "attendance/teacher_attendance.html",
        {
            "group": group,
            "student_records": student_records,
            "attendance_date": attendance_date,
            "session_number": session_number,
            "allowed_sessions": allowed_sessions,
            "sessions_list": [1, 2, 3, 4],
        },
    )


@admin_required
def justification_list(request):
    justifications = (
        Justification.objects.select_related("student")
        .prefetch_related("session_links")
        .all()
        .order_by("-date")
    )

    total = justifications.count()
    approved = sum(1 for j in justifications if j.status == "Approved")
    pending = sum(1 for j in justifications if j.status == "Pending")
    rejected = sum(1 for j in justifications if j.status == "Rejected")

    approved_rate = round((approved / total) * 100) if total > 0 else 0

    context = {
        "justifications": justifications,
        "stats": {
            "total": total,
            "approved": approved,
            "pending": pending,
            "rejected": rejected,
            "approved_rate": approved_rate,
        },
    }
    return render(request, "attendance/justifications.html", context)


@admin_required
def justification_create(request):
    if request.method == "POST":
        form = JustificationForm(request.POST, request.FILES)
        if form.is_valid():
            justification = form.save()
            sessions = form.cleaned_data["sessions"]
            for s in sessions:
                JustificationSession.objects.create(
                    justification=justification, session_number=int(s)
                )
            messages.success(request, "Justification added successfully.")
            return redirect("attendance:justification_list")
    else:
        form = JustificationForm()
    return render(request, "attendance/justification_form.html", {"form": form})


@admin_required
def justification_approve(request, pk):
    justif = get_object_or_404(Justification, pk=pk)
    justif.status = "Approved"
    justif.save()
    messages.success(request, "Justification approved successfully.")

    next_url = request.GET.get("next") or request.POST.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("attendance:justification_list")


@admin_required
def justification_reject(request, pk):
    justif = get_object_or_404(Justification, pk=pk)
    justif.status = "Rejected"
    justif.save()
    messages.success(request, "Justification rejected successfully.")

    next_url = request.GET.get("next") or request.POST.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("attendance:justification_list")


@login_required
def student_submit_justification(request):
    if request.user.role != "stagiaire":
        messages.error(request, "Only students can submit justifications.")
        return redirect("dashboard:index")

    student = request.user.student

    if request.method == "POST":
        form = StudentJustificationForm(request.POST, request.FILES)
        attendance_date = request.POST.get("date")

        if not attendance_date:
            messages.error(request, "Please select a date.")
            return redirect("attendance:student_submit_justification")

        try:
            date_obj = date.fromisoformat(attendance_date)
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect("attendance:student_submit_justification")

        if form.is_valid():
            # Validation 1: Prevent duplicate justification for the same date
            if Justification.objects.filter(student=student, date=date_obj).exists():
                messages.error(
                    request,
                    f"You have already submitted a justification for {attendance_date}.",
                )
                return redirect("attendance:student_submit_justification")

            # Validation 2: Find all 'Absent' sessions for this student on this date
            absent_sessions = AttendanceSession.objects.filter(
                student=student, date=date_obj, status="Absent"
            )

            if not absent_sessions.exists():
                messages.error(
                    request,
                    "You cannot submit a justification because you have no 'Absent' sessions on this date.",
                )
                return render(
                    request,
                    "attendance/student_justification_form.html",
                    {"form": form, "selected_date": attendance_date},
                )

            # Save the justification
            justification = form.save(commit=False)
            justification.student = student
            justification.date = date_obj
            justification.status = "Pending"
            justification.save()

            # Automatically link to ALL absent sessions for this date
            for s in absent_sessions:
                JustificationSession.objects.create(
                    justification=justification, session_number=s.session_number
                )

            messages.success(
                request, "Your justification has been submitted and is pending review."
            )
            return redirect("dashboard:student_dashboard")
    else:
        form = StudentJustificationForm()
        attendance_date = request.GET.get("date")

    return render(
        request,
        "attendance/student_justification_form.html",
        {"form": form, "selected_date": attendance_date},
    )


# --- REPORTS & EXPORT ---

from .reports import generate_attendance_csv, get_attendance_report_data
from students.models import Student


@admin_required
def attendance_report(request):
    groups = Group.objects.all()
    students = Student.objects.all()

    qs = AttendanceSession.objects.all()

    # Filtering
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    group_id = request.GET.get("group_id")
    student_id = request.GET.get("student_id")

    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)
    if group_id:
        qs = qs.filter(group_id=group_id)
    if student_id:
        qs = qs.filter(student_id=student_id)

    report_data = get_attendance_report_data(qs)

    context = {
        "groups": groups,
        "students": students,
        "report_data": report_data,
        "start_date": start_date,
        "end_date": end_date,
        "selected_group": int(group_id) if group_id else None,
        "selected_student": int(student_id) if student_id else None,
    }
    return render(request, "attendance/report.html", context)


@admin_required
def attendance_export_csv(request):
    qs = AttendanceSession.objects.all()

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    group_id = request.GET.get("group_id")
    student_id = request.GET.get("student_id")

    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)
    if group_id:
        qs = qs.filter(group_id=group_id)
    if student_id:
        qs = qs.filter(student_id=student_id)

    return generate_attendance_csv(qs)


@admin_required
def attendance_export_pdf_view(request):
    """
    Returns a printable HTML layout designed to be exported as PDF via browser print.
    """
    qs = AttendanceSession.objects.all()

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    group_id = request.GET.get("group_id")
    student_id = request.GET.get("student_id")

    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)
    if group_id:
        qs = qs.filter(group_id=group_id)
    if student_id:
        qs = qs.filter(student_id=student_id)

    report_data = get_attendance_report_data(qs)

    context = {
        "report_data": report_data,
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "attendance/report_print.html", context)
