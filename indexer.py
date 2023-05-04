# -*- coding: utf-8 -*-
""" Extracts files, pages, assignments and folders from all coureses in a term.
    All the data is saved as a json file to converted into a search index usable 
    in PowerBI or PowerQuery for Excel.
"""
import json
import csv
from lib.Canvas import GetData as gcd

THROTTLE_COUNTER = 0  # Throttle counter

def handler (end_point, params):
    global THROTTLE_COUNTER
    data = gcd(end_point, THROTTLE_COUNTER, params)
    response = data.fetch()
    THROTTLE_COUNTER += data.throttle_count
    return response


ROOT_ACCT = 1 # Root account ID (probably 1)
MAIN_SUBACCT = 2  # Main subaccount ID, where children are sub-accounts
SUBACCT_IDS = "1,2,3"  # Sub-account IDs to search
TOPN = 1  # Number of terms to search
COURSE_NAME_FILTER_EXCLUDE = [" 299", " 45"]  # Exclude courses with the name filter in the name

# List active courses in an account
courses = []
api_endpoint = "/api/v1/accounts/{main_account}/courses".format(main_account=MAIN_SUBACCT)
courses_unhandled = gcd(api_endpoint, THROTTLE_COUNTER)  # Not using hanlder to reuse the same object
for term in courses_unhandled.get_terms(TOPN):
    params = {"enrollment_type[]": ["student"],"with_enrollments": [True],"published": [True],
              "by_subaccounts": ["{subaccount_ids}".format(subaccount_ids=SUBACCT_IDS)],
              "enrollment_term_id": [term]}
    courses_unhandled.change_params(params)
    for course in courses_unhandled.fetch():
        if COURSE_NAME_FILTER_EXCLUDE == None:
            courses.append(course)
        else:
            keep = True
            for exclude_text in COURSE_NAME_FILTER_EXCLUDE:
                if course["name"].find(exclude_text) != -1:
                    keep = False
            if keep:
                courses.append(course)

extract = {}
index = [["course_id","id", "name", "url", "type","content", "created_at","updated_at", "available", "inbound_links"]]
for course in courses:
    # Get a list of all pages and store in index
    course_id = course["id"]
    extract[course_id] = {}
    api_endpoint = "/api/v1/courses/{course_id}/pages"
    pages = handler(api_endpoint.format(course_id=course_id), {"sort": ["updated_at"], "order": ["desc"]})
    extract[course_id]["pages"] = {}
    for page in pages:
        page_id = page["page_id"]
        extract[course_id]["pages"][page_id] = page

    # Get all page contents and store in index
    for page in pages:
        api_endpoint="/api/v1/courses/{course_id}/pages/{id}"
        page_id = page["page_id"]
        content = handler(api_endpoint.format(course_id=course_id, id=page_id), None)
        extract[course_id]["pages"][page_id]["content"] = content 
    
    # log all pages and page information
    for page in extract[course_id]["pages"]:
        page_id = page
        page_name = extract[course_id]["pages"][page]["title"]
        page_url = extract[course_id]["pages"][page]["html_url"]
        page_type = "page"
        page_content = extract[course_id]["pages"][page]["content"]["body"]
        page_created_at = extract[course_id]["pages"][page]["created_at"]
        page_updated_at = extract[course_id]["pages"][page]["updated_at"]
        page_available = extract[course_id]["pages"][page]["published"]
        page_links = ""
        index.append([course_id, page_id, page_name, page_url, page_type, page_content, page_created_at,
                      page_updated_at, page_available, page_links])
        
    # Get all assignments and store in index
    api_endpoint = "/api/v1/courses/{course_id}/assignments"
    assignments = handler(api_endpoint.format(course_id=course_id), None)
    extract[course_id]["assignments"] = assignments
    for assignment in assignments:
        assignment_id = assignment["id"]
        assignment_name = assignment["name"]
        assignment_url = assignment["html_url"]
        assignment_type = "assignment"
        assignment_content = assignment["description"]
        assignment_created_at = assignment["created_at"]
        assignment_updated_at = assignment["updated_at"]
        assignment_available = assignment["workflow_state"]
        assignment_links = ""
        index.append([course_id, assignment_id, assignment_name, assignment_url, assignment_type, assignment_content,
                      assignment_created_at, assignment_updated_at, assignment_available, assignment_links])

    # Get all modules and store in index
    api_endpoint = "/api/v1/courses/{course_id}/modules"
    modules = handler(api_endpoint.format(course_id=course_id), None)
    extract[course_id]["modules"] = modules
    for module in modules:
        module_id = module["id"]
        module_name = module["name"]
        module_url = module["items_url"]
        module_type = "module"
        module_content = ""
        module_created_at = ""
        module_updated_at = ""
        module_available = module["published"]
        module_links = ""
        index.append([course_id, module_id, module_name, module_url, module_type, module_content, module_created_at,
                      module_updated_at, module_available, module_links])

    # Get all files and store in index
    api_endpoint = "/api/v1/courses/{course_id}/files"
    files = handler(api_endpoint.format(course_id=course_id), None)
    extract[course_id]["files"] = files
    PAGES_SEARCH_STR = "files/{file_id}"
    for file in extract[course_id]["files"]:
        file["linked_page_id"] = []
        text_to_find = PAGES_SEARCH_STR.format(file_id=file["id"])
        for page in extract[course_id]["pages"]:
            page_id = page
            if not isinstance(extract[course_id]["pages"][page]["content"]["body"], type(None)) and extract[course_id]["pages"][page]["content"]["body"].find(text_to_find) != -1:
                file["linked_page_id"].append("id_" + str(page_id))
    for file in files:
        file_id = file["id"]
        file_name = file["display_name"]
        file_url = file["url"]
        file_type = "file"
        file_content = ""
        file_created_at = file["created_at"]
        file_updated_at = file["modified_at"]
        file_available = not(file["hidden"])
        file["linked_page_id"] = [str(i) for i in file["linked_page_id"]]
        file_links = ",".join(file["linked_page_id"])
        index.append([course_id, file_id, file_name, file_url, file_type, file_content, file_created_at, file_updated_at, file_available, file_links])

# Make all values in index valid for CSV
legal_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~:/?#[]@!$&'()*+,;=%<>{}|\\^\"`"
for row in index:
    for i, value in enumerate(row):
        if isinstance(value, str):
            row[i] = "".join(c for c in value if c in legal_chars)
        else:
            row[i] = str(value)

# Write index to file
with open("data/index.csv", "w", encoding="utf-8") as f:
    writer = csv.writer(f, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL, newline='')
    writer.writerows(index)

# Write extract to JSON file for later use (may be large)
with open("data/extract.json", "w", encoding="utf-8") as f:
    json.dump(extract, f, indent=4, sort_keys=True)

