import json
import datetime
from lib.Canvas import GetData as gcd
global THROTTLE_COUNTER # Throttle counter
THROTTLE_COUNTER = 0

def handler (end_point, params):
    global THROTTLE_COUNTER
    data = gcd(end_point, THROTTLE_COUNTER, params)
    response = data.fetch()
    THROTTLE_COUNTER += data.throttle_count
    return response

main_account = 1
subaccount_ids = "1,2,3"

# List active courses in an account
EPSTR = "/api/v1/accounts/{main_account}/courses".format(main_account=main_account)
params = {"enrollment_type[]": ["student"],
          "with_enrollments": [True],
          "published": [True],
          "by_subaccounts": ["{subaccount_ids}".format(subaccount_ids=subaccount_ids)],
          "starts_before": [(datetime.datetime.now() - datetime.timedelta(days=420)).isoformat()],
          "ends_before": [(datetime.datetime.now() + datetime.timedelta(60)).isoformat()]}
courses = handler(EPSTR.format(account_id=1), params)

index = {}
for course in courses:
    # Get a list of all pages and store in index
    course = course["id"]
    index[course] = {}
    EPSTR = "/api/v1/courses/{course_id}/pages"
    pages = handler(EPSTR.format(course_id=course["id"]), {"sort": ["updated_at"], "order": ["desc"]})
    index[course]["pages"] = pages

    # Get all page contents and store in index
    for page in pages:
        EPSTR="/api/v1/courses/{course_id}/pages/{id}"
        page_id = page["page_id"]
        content = handler(EPSTR.format(course_id=course, id=page_id), None)
        index[course][page_id] = content
    
    # Get course-level student summary data
    EPSTR = "/api/v1/courses/{course_id}/analytics/student_summaries"
    student_summaries = handler(EPSTR.format(course_id=course), {"sort_column": ["page_views_descending"]})
        

    # Get all assignments and store in index
    EPSTR = "/api/v1/courses/{course_id}/assignments"
    assignments = handler(EPSTR.format(course_id=course), None)
    index[course]["assignments"] = assignments

    # Get all modules and store in index
    EPSTR = "/api/v1/courses/{course_id}/modules"
    modules = handler(EPSTR.format(course_id=course), None)
    index[course]["modules"] = modules

# Export all to JSON file
with open("data/index.json", "w") as f:
    json.dump(index, f, indent=4)






