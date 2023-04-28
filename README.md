# Canvas Course Indexer
This script takes a canvas instance url and token and indexes all courses in the previous N terms. Terms are calculated for my institution.

Simply clone this repository, create a virtual environment, use pip to install requests. The entire export will be saved as a json file for later analysis. The index itself will be saved as a CSV file.

Upcoming changes:
- Other tabulations to make sure the highest results are the best (inspired by what little I know about the Google search algo)
  - Number of inbound links in assignments to other pages and files
  - Number of inbound links in modules to other files, pages, assignments
  - Number of inbound links in accouncements to other files, pages, assignments
- Extraction/compression of hyperlinks found in a page and assignment and stored as a delimited list in the cell
- Strip out all HTML tags with beautiful soup for cleaner search experience
