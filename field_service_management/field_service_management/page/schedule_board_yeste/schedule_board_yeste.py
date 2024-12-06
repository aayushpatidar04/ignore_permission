import frappe
from frappe import _
import json
from datetime import datetime
from datetime import timedelta


@frappe.whitelist()
def get_context(context=None):
    context = context or {}
    user = frappe.session.user

    issues = []
    technicians = []
      
    if user == "Administrator":
        issues = frappe.get_all(
            "Maintenance Visit",
            filters={"_assign": ""},
            fields=[
                "name",
                "subject",
                "status",
                "creation",
                "maintenance_type",
                "_assign",
                "description",
                "maintenance_description",
                "customer_address",
                "completion_status"
            ],
        )
        technicians = frappe.get_all(
            "User",
            filters={"role_profile_name": "Service Technician Role Profile"},
            fields=["email", "user_image", "full_name"],
        )
    role_profile = frappe.db.get_value("User", user, "role_profile_name")
    if role_profile == "Service Coordinator Profile":
        # Fetch the user's territory from User Permissions
        
        territory = frappe.db.get_value(
            "User Permission", {"user": user, "allow": "Territory"}, "for_value"
        )
        # Fetch issues based on the user's territory
        issues = frappe.get_all(
            "Maintenance Visit",
            filters={"territory": territory, "_assign": ""},
            fields=[
                "name",
                "subject",
                "status",
                "creation",
                "maintenance_type",
                "_assign",
                "description",
                "maintenance_description",
                "customer_address",
                "completion_status"
            ],
        )
        technicians = frappe.get_all(
            "User",
            filters={"role_profile_name": "Service Technician Role Profile"},
            fields=["email", "user_image", "full_name"],
        )
        # Filter technicians based on their territory in User Permission
        technician_list = []
        for tech in technicians:
            tech_territory = frappe.db.get_value(
                "User Permission", {"user": tech["email"], "allow": "Territory"}, "for_value"
            )
            if tech_territory == territory:
                technician_list.append(tech)
        technicians = technician_list
    for issue in issues:
        if issue._assign:
            try:
                assign_list = json.loads(issue._assign)
                issue.assigned = json.loads(issue._assign)
                issue._assign = " | ".join(assign_list)
            except json.JSONDecodeError:
                issue._assign = "No one assigned"

        #geolocation --------------------------------------------------
        geolocation = frappe.get_all('Address', filters = {'name' : issue.customer_address}, fields = ['geolocation'])
        geolocation = json.loads(geolocation[0].geolocation)
        print(geolocation)
        issue.geolocation = json.dumps(geolocation['features']).replace('"', "'")
        # issue.geolocation = geolocation
        # checklist tree ----------------------------------------------
        checklist = frappe.get_all(
            "Maintenance Visit Checklist",
            filters = {"parent": issue.name},
            fields = ['item_code', 'item_name', 'heading', 'work_done', 'done_by']
        )
        checklist_tree = {}
        html_content = ""
        for problem in checklist:
            key = problem.item_code
            if key not in checklist_tree:
                checklist_tree[key] = []
            checklist_tree[key].append(problem)

        for item_code, products in checklist_tree.items():
            if products:
                html_content += f"<p><strong>{item_code}: {products[0].item_name}</strong></p>"
                for product in products:
                    checked_attribute = "checked" if product.work_done == "Yes" else ""
                    html_content += f"<p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<input type='checkbox' {checked_attribute} disabled> &nbsp;&nbsp;&nbsp;&nbsp;{product.heading}<br>"
                html_content += "</p>"
        issue.checklist_tree = html_content


        # Products -------------------------------------------------------------
        products = frappe.get_all(
            "Maintenance Visit Purpose",
            filters = {"parent": issue.name},
            fields = ['item_code', 'item_name', 'custom_image']
        )
        issue.products = products

        # Spare Items -------------------------------------------------------------
        spare_items = frappe.get_all(
            "Spare Part",
            filters = {"parent": issue.name},
            fields = ['item_code', 'description', 'periodicity', 'uom']
        )
        issue.spare_items = spare_items

        #symptoms and resolutions ------------------------------------------------------
        symptoms = frappe.get_all(
            "Maintenance Visit Symptoms",
            filters = {"parent": issue.name},
            fields = ['item_code', 'symptom_code', 'resolution', 'image']
        )
        symptoms_res = {}
        html_content = ""
        for symptom in symptoms:
            key = symptom.item_code
            if key not in symptoms_res:
                symptoms_res[key] = []
            symptoms_res[key].append(symptom)

        for item_code, resolutions in symptoms_res.items():
            if resolutions:
                html_content += f"<p><strong>{item_code}:</strong></p>"
                for resolution in resolutions:
                    html_content += f"<p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<img src='{resolution.image}' style='max-width: 100px;'> --> <strong>{resolution.symptom_code}</strong> --> {resolution.resolution}<br>"
                html_content += "</p>"
        issue.symptoms_res = html_content


    context["issues"] = issues
    
    date = datetime.now().date()
    date = date - timedelta(days=1)
    time_slots = [
        {"label": "09:00 AM", "time": timedelta(hours=9)},
        {"label": "10:00 AM", "time": timedelta(hours=10)},
        {"label": "11:00 AM", "time": timedelta(hours=11)},
        {"label": "12:00 PM", "time": timedelta(hours=12)},
        {"label": "01:00 PM", "time": timedelta(hours=13)},
        {"label": "02:00 PM", "time": timedelta(hours=14)},
        {"label": "03:00 PM", "time": timedelta(hours=15)},
        {"label": "04:00 PM", "time": timedelta(hours=16)},
        {"label": "05:00 PM", "time": timedelta(hours=17)},
        {"label": "06:00 PM", "time": timedelta(hours=18)},
        {"label": "07:00 PM", "time": timedelta(hours=19)},
        {"label": "08:00 PM", "time": timedelta(hours=20)},
    ]
    for tech in technicians:
        html_content = ""
        tasks = frappe.get_all(
            "Assigned Tasks",
            filters={"date": date, "technician": tech.email},
            fields=["issue_code", "stime", "etime", "rescheduled"],
        )
        for task in tasks:
            time_diff = task.etime - task.stime
            task.duration_in_hours = time_diff.total_seconds() / 3600
            task.flag = 0
        tech.tasks = tasks
        count = 0
        total_hours = 0

        for slot in time_slots:
            if slot['label'] == '12:00 PM':
                html_content += f'<div style="width: 100px; border-right: 1px solid #000; color: white; background-color: red;" data-time="{slot["time"]}" data-tech="{tech.email}" class="px-1">Lunch Time</div>'
            else:
                not_available = []
                ts = frappe.get_all(
                    "Assigned Tasks",
                    filters={"date": date},
                    fields=["issue_code", "stime", "etime", "rescheduled", "technician"],
                )
                for t in ts:
                    if t.stime <= slot["time"] and t.etime > slot["time"]:
                        not_available.append(t.technician)
                slot['not_available'] = not_available
                task_in_slot = None
                for task in tasks:
                    maintenance = frappe.get_doc('Maintenance Visit', task.issue_code)
                    if task.stime <= slot["time"] and task.etime > slot["time"]:
                        if task.flag == 0:  # Check if not already displayed
                            task_in_slot = task
                            task.flag = 1  # Mark as displayed
                            break
                if task_in_slot:
                    total_hours += task_in_slot['duration_in_hours']
                    html_content += f"""
                    <div style="width: {task_in_slot['duration_in_hours'] * 100}px; background-color: red; border-right: 1px solid #000; padding: 10px; cursor: grab; user-select: none;" class="px-1 py-2 text-white text-center drag" data-type="type2" draggable="true" id="task-{task_in_slot['issue_code']}" data-duration="{task_in_slot['duration_in_hours']}">
                        <a href="javascript:void(0)"
                            class="text-white" data-toggle="modal"
                            data-target="#taskModaltask-{task_in_slot['issue_code']}">{task_in_slot['issue_code']}</a>
                    </div>
                    """
                    html_content += f"""
                    <div class="modal fade" id="taskModaltask-{task_in_slot['issue_code']}" tabindex="-1" role="dialog"
                        aria-labelledby="taskModalLabel{task_in_slot['issue_code']}" aria-hidden="true">
                        <div class="modal-dialog" role="document" style="max-width: 80%; margin: 1.75rem auto">
                            <div class="modal-content">
                                <div class="modal-header">
                                    <h5 class="modal-title" id="taskModalLabel{task_in_slot['issue_code']}">{task_in_slot['issue_code']}</h5>
                                    <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                        <span aria-hidden="true">&times;</span>
                                    </button>
                                </div>
                                <div class="modal-body">
                                    <form id="custom2-form-{task_in_slot['issue_code']}" class="custom-form" method="POST">
                                        <label for="code">Maintenance Visit Code:</label>
                                        <input class="form-control code" type="text" name="code" value="{task_in_slot['issue_code']}" required
                                            readonly><br><br>

                                        <label for="technician">Select Co-Technicians (<span class="text-danger">only if more than one technician required</span>):</label><br>
                                        <select class="form-select technician" style="width:100%" name="technician[]" multiple="multiple" required>"""
                    for item in technicians:
                        selected = 'selected' if item.email in maintenance._assign else ''
                        html_content += '<option value="{email}" {selected}>{email}</option>'.format(
                            email=item.email,
                            selected=selected
                        )                                   
                    html_content += """ </select><br><br>

                                        <label for="date">Date:</label>
                                        <input class="form-control date" type="date" name="date" value="{date}" required><br><br>

                                        <label for="stime">Start Time</label>
                                        <input class="form-control stime" type="time" name="stime" value="{stime}" required readonly><br><br>
                                        
                                        <label for="etime">End Time:</label>
                                        <input class="form-control etime" type="time" name="etime" value="{etime}" required readonly>
                                        <small><span class="text-danger etime-error"></span></small><br><br>

                                        <button type="button" class="update btn btn-success"
                                            data-issue="{issue_code}">Update</button>
                                    </form>
                                </div>
                            </div>
                        </div>
                    </div>""".format(issue_code=task_in_slot['issue_code'], date=date, stime=task_in_slot['stime'], etime=task_in_slot['etime'])
                    count += task_in_slot["duration_in_hours"] - 1
                else:
                    if count == 0:
                        html_content += f'<div style="width: 100px; border-right: 1px solid #000; background-color: cyan;" data-time="{slot["time"]}" data-tech="{tech.email}" data-na="{slot["not_available"]}" class="px-1">-</div>'
                    elif count % 1 == 0.5:
                        slot['time'] += timedelta(minutes=30)
                        html_content += f'<div style="width: 50px; border-right: 1px solid #000; background-color: cyan;" data-time="{slot["time"]}" data-tech="{tech.email}" data-na="{slot["not_available"]}" class="px-1">-</div>'
                        count -= 0.5
                    else:
                        count -= 1
        tech.html_content = html_content
        percent_occupied = round((total_hours) / 11 * 100, 2)
        tech.total_hours = percent_occupied
    context["technicians"] = technicians    
    context["slots"] = time_slots
    context["message"] = "Welcome to your schedule board!"
    return context


@frappe.whitelist()
def save_form_data(form_data):
    # Parse the form_data from the request
    try:
        form_data = json.loads(form_data)
        technicians = form_data["technicians"]
        code = form_data["code"]
        date = form_data["date"]
        etime = form_data["etime"]
        stime = form_data["stime"]
        hours, minutes = map(int, etime.split(":"))
        etime = timedelta(hours=hours, minutes=minutes)
        hours, minutes = map(int, stime.split(":"))
        stime = timedelta(hours=hours, minutes=minutes)
        for tech in technicians:
            assigned_tasks = frappe.get_all(
                "Assigned Tasks",
                filters={"technician": tech, "date": date},
                fields=["issue_code", "stime", "etime"],
            )
            for task in assigned_tasks:
                if (
                    (stime > task.stime and stime < task.etime)
                    or (etime > task.stime and etime < task.etime)
                    or (task.stime > stime and task.stime < etime)
                ):
                    return {
                        "error": "error",
                        "message": f"Time Slot Clash for technician: {tech}",
                    }

        for tech in technicians:

            new_doc = frappe.get_doc(
                {
                    "doctype": "Assigned Tasks",
                    "issue_code": code,
                    "technician": tech,
                    "date": date,
                    "etime": etime,
                    "stime": stime,
                }
            )
            new_doc.insert()

        # Optionally, you can update the Issue doctype as well
        issue_doc = frappe.get_doc("Maintenance Visit", code)
        if issue_doc:
            existing_techs = json.loads(issue_doc._assign) if issue_doc._assign else []
            for tech in technicians:
                if tech not in existing_techs:
                    existing_techs.append(tech)
            issue_doc._assign = json.dumps(existing_techs)
            frappe.db.sql(
                """
                UPDATE `tabMaintenance Visit` SET `_assign` = %s, `maintenance_type` = %s WHERE name = %s
            """,
                (json.dumps(existing_techs), 'Scheduled', code),
            )

            frappe.db.commit()
        return {"success": "success"}
    except Exception as e:
        return {"error": "error", "message": str(e)}


@frappe.whitelist()
def get_cords():
    query = """
    SELECT technician, latitude, longitude, time 
    FROM `tabLive Location` 
    WHERE (technician, time) IN (
        SELECT technician, MAX(time) 
        FROM `tabLive Location` 
        GROUP BY technician
    )
    """
    technicians = frappe.db.sql(query, as_dict=True)
    
    return technicians



@frappe.whitelist()
def update_form_data(form_data):
    # # Parse the form_data from the request
    # pass
    try:
        form_data = json.loads(form_data)
        technicians = form_data["technicians"]
        code = form_data["code"]
        date = form_data["date"]
        etime = form_data["etime"]
        stime = form_data["stime"]
        if(len(etime) > 5):
            hours, minutes, seconds = map(int, etime.split(":"))
        else:
            hours, minutes = map(int, etime.split(":"))
        etime = timedelta(hours=hours, minutes=minutes)
        if(len(stime) > 5):
            hours, minutes, seconds = map(int, stime.split(":"))
        else:
            hours, minutes = map(int, stime.split(":"))

        stime = timedelta(hours=hours, minutes=minutes)


        tasks = frappe.get_all("Assigned Tasks", filters={"issue_code": code}, fields=["name"])

        if tasks:
            for task in tasks:
                frappe.delete_doc("Assigned Tasks", task.name, force=True)
            frappe.db.commit()



        for tech in technicians:
            assigned_tasks = frappe.get_all(
                "Assigned Tasks",
                filters={"technician": tech, "date": date},
                fields=["issue_code", "stime", "etime"],
            )
            for task in assigned_tasks:
                if (
                    (stime > task.stime and stime < task.etime)
                    or (etime > task.stime and etime < task.etime)
                    or (task.stime > stime and task.stime < etime)
                ):
                    return {
                        "error": "error",
                        "message": f"Time Slot Clash for technician: {tech}",
                    }

        for tech in technicians:

            new_doc = frappe.get_doc(
                {
                    "doctype": "Assigned Tasks",
                    "issue_code": code,
                    "technician": tech,
                    "date": date,
                    "etime": etime,
                    "stime": stime,
                }
            )
            new_doc.insert()

        # Optionally, you can update the Issue doctype as well
        issue_doc = frappe.get_doc("Maintenance Visit", code)
        if issue_doc:
            existing_techs = []
            for tech in technicians:
                if tech not in existing_techs:
                    existing_techs.append(tech)
            if existing_techs:
                issue_doc._assign = json.dumps(existing_techs)
                frappe.db.sql(
                    """
                    UPDATE `tabMaintenance Visit` SET `_assign` = %s WHERE name = %s
                    """,
                    (json.dumps(existing_techs), code),
                )
            else:
                issue_doc._assign = ""
                frappe.db.sql(
                """
                    UPDATE `tabMaintenance Visit` SET `_assign` = %s, `maintenance_type` = %s WHERE name = %s
                """,
                    ("", 'Unscheduled', code),
                )

            frappe.db.commit()
        return {"success": "success"}
    except Exception as e:
        return {"error": "error", "message": str(e)}
    

@frappe.whitelist()
def get_live_locations():

    technicians = []
    maintenance_visits = []
    technician_records = frappe.db.sql("""
        SELECT technician, latitude, longitude, time 
        FROM `tabLive Location` 
        WHERE (technician, time) IN (
            SELECT technician, MAX(time) 
            FROM `tabLive Location` 
            GROUP BY technician
        )
        """, as_dict=True)
    for tech in technician_records:
        technicians.append({
            "technician": tech.technician,
            "latitude": tech.latitude,
            "longitude": tech.longitude
        })
    
    maintenance_records = frappe.db.sql("""
        SELECT name, address_html, delivery_address
        FROM `tabMaintenance Visit`
        WHERE completion_status != 'Fully Completed'
    """, as_dict=True)
    

    for visit in maintenance_records:
        visit_doc = frappe.get_doc("Maintenance Visit", visit.name)

        #geolocation
        delivery_note_name = frappe.get_value(
            "Delivery Note",
            {"shipping_address": visit_doc.delivery_address},
            "name"  # Fetch the name of the Delivery Note
        )
        if not delivery_note_name:
            frappe.throw(f"No Delivery Note found for address: {visit_doc.delivery_address}")
        delivery_note = frappe.get_doc("Delivery Note", delivery_note_name)
        address = frappe.get_doc("Address", delivery_note.shipping_address_name)
        geolocation = address.geolocation
        if not geolocation:
            frappe.throw(f"No geolocation found for address: {address.name}")
        geolocation = json.loads(geolocation)

        maintenance_visits.append({
            "visit_id": visit.name,
            "geolocation": geolocation,
            "address": visit.address_html
        })    
    return {
        "technicians": technicians,
        "maintenance": maintenance_visits
    }


