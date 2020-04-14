import argparse
import codecs
import json
from operator import itemgetter
from notion.client import *
from notion.block import *
from notion.user import User
from datetime import datetime
import dateutil.parser


def parse_args():
    parser = argparse.ArgumentParser(
        description='Export your Wunderlist content to Notion'
    )
    parser.add_argument(
        'wunderlist_backup',
        type=str,
        help='Wunderlist backup file (json)'
    )

    return parser.parse_args()

def configure_and_load(in_wunderlist_backup_file):

    client_a = NotionClient(token_v2="tokena")
    client_b = NotionClient(token_v2="tokenb")
    root_page = client_a.get_block("https://www.notion.so/toplevelpage")
    user_a = client_a.get_user("b7f6a072-99ae-4e73-a0c7-4c6afca12bdb")
    user_b = client_a.get_user("5953ecd8-492a-4ab9-8b66-v993ca9070b6")
    user_a_email = "abc@example.com"

    # Build a list of existing Notion folders (pages with title but no collection)
    notion_folders = {}
    for page in root_page.children:
        # print(page)
        if page.title and not hasattr(page,'collection'):
            notion_folders[page.title] = page

    with open('ignore_list_ids.txt', 'r+', 1) as ignore_file:
        load_content(in_wunderlist_backup_file, client_a, client_b, root_page, user_a, user_b, notion_folders, ignore_file, user_a_email)


def load_content(in_wunderlist_backup_file, client_a, client_r, root_page, user_a, user_b, notion_folders, ignore_file, user_a_email):
    
    ignore_file_lines_raw = ignore_file.readlines()
    ignore_file_lines = filter(lambda x: x[0] != '#', ignore_file_lines_raw)
    ignore_wlist_ids = list(map(lambda x: int(x.split(' ')[0]), ignore_file_lines))
    print('Ignored lists: {}'.format(ignore_wlist_ids))

    with open(in_wunderlist_backup_file) as json_file:
        json_string = json_file.read().encode().decode('utf-8-sig')
        wunderlist_content = json.loads(json_string)
        # print(wunderlist_content)
        for wlist_ix, wlist in enumerate(wunderlist_content,1):
            wlist_title = wlist['title']
            wlist_id = wlist['id']
            wlist_folder = 'No Folder' if wlist['folder'] is None else wlist['folder']['title']

            # if wlist_folder != 'Alex': # or wlist_folder == 'No Folder': # and (wlist_title == 'Groceries' or wlist_title == 'Make'):
            if wlist_id in ignore_wlist_ids: # don't process lists we aleady processed before
                print('Ignoring list {}'.format(wlist_title))
            else:
                print (u'Processing Wunderlist list "{}" id {} ({}/{}) in Folder {}'.format(
                    wlist_title,
                    wlist_id,
                    wlist_ix,
                    len(wunderlist_content),
                    wlist_folder
                ))
                if (wlist_folder not in notion_folders):
                    notion_folder = root_page.children.add_new(PageBlock, title=wlist_folder)
                    notion_folders[wlist_folder] = notion_folder
                else:
                    notion_folder = notion_folders[wlist_folder]
                cvb_a = notion_folder.children.add_new(CollectionViewPageBlock)
                cvb_a.collection = client_a.get_collection(
                    client_a.create_record("collection", parent=cvb_a, schema=get_collection_schema())#, query=query2)
                )
                cvb_a.title = wlist['title']
                bview = cvb_a.views.add_new(view_type="board")
                bview.name = 'Board'

                # Doesn't work, STAT just needs to be first groupable schema property by name alphabetically
                # bview.query = query2
                # bview.group_by = "STAT"

                tview = cvb_a.views.add_new(view_type="table")
                tview.name = 'Table'

                cvb_b = client_r.get_block(cvb_a.id) # Get handle on CollectionViewBlock using Raquel client, for createdBy

                cnt = 0
                for task_ix, task in enumerate(wlist['tasks'],1):
                    print (u'Processing "{}" / "{}" ({}/{})'.format(
                        wlist['title'],
                        task['title'],
                        task_ix,
                        len(wlist['tasks'])
                    ))
                    createdbyEmail = None if task["createdBy"] is None else task["createdBy"]["email"]
                    createdby = [] if createdbyEmail is None else user_a if createdbyEmail == user_a_email else user_b
                    if createdby == user_a:
                        cvb = cvb_a
                    else:
                        cvb = cvb_b
                    notes = ''
                    rawnotes = task['notes']
                    rawurls = []
                    tag = None
                    if rawnotes:
                        notes = rawnotes[0]['content']
                        rawurls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', notes)
                        isRecipe = len(re.findall('ngredient', notes)) >= 1 or len(re.findall('[Rr]ecipe', notes)) >= 1
                        tag = 'recipe' if isRecipe else None
                    link = ''
                    if rawurls:
                        link = rawurls[0]
                    status = "Completed" if task["completedAt"] is not None else "Starred" if task["starred"] == True else None
                    assigneeEmail = None if task["assignee"] is None else task["assignee"]["email"]
                    assignee = [] if assigneeEmail is None else user_a if assigneeEmail == user_a_email else user_b
                    row = cvb.collection.add_row(
                        name=task['title'],
                        title=task['title'],
                        status=status,
                        tags=tag,
                        assignee=assignee,
                        link=link,
                        files=[],
                        created_at=parse_date(task["createdAt"]),
                        created_by=createdby,
                        updated_at=parse_date(task["createdAt"]),
                        updated_by=createdby
                    )
                    if len(task['subtasks']) > 0:
                        subtasksblock = row.children.add_new(ColumnBlock)
                        for subtask in task['subtasks']:
                            stblock = subtasksblock.children.add_new(TodoBlock, title=subtask['title'], checked=subtask['completed'])                    
                    if notes:
                        row.children.add_new(
                            TextBlock, title=notes
                        )
                    cnt += 1
                    # if cnt > 100:
                    #     break
                # for task end
                ignore_log = '{} - {} / {}\n'.format(
                    wlist_id,
                    wlist_folder,
                    wlist_title
                )
                print(ignore_log)
                ignore_file.write(ignore_log)
                    

def get_collection_schema():
    return {
        "title": {"name": "Name", "type": "title"},        
        "STAT": {
            "name": "Status",
            "type": "select",
            "options": [
                {
                    "color": "red",
                    "id": "9560dab-c776-43d1-9420-27f4011fcaec",
                    "value": "Starred",
                },
                {
                    "color": "green",
                    "id": "002c7016-ac57-413a-90a6-64afadfb0c44",
                    "value": "Completed",
                },
            ],
        },
        "TAGS": {
            "name": "Tags",
            "type": "multi_select",
            "options": [
                {
                    "color": "default",
                    "id": "79560dab-c776-43d1-9420-27f4011fcaec",
                    "value": "recipe",
                },
            ],
        },
        "WHOS": {"name": "Assignee", "type": "person"},
        "LINK": {"name": "Link", "type": "url"},
        "FILE": {"name": "Files", "type": "file"},
        "CREA": {"name": "Created At", "type": "created_time"},
        "CRUS": {"name": "Created By", "type": "created_by"},        
        "UPDA": {"name": "Updated At", "type": "last_edited_time"}, # 1587143220000 1587133220000 1587123220000
        "UPUS": {"name": "Updated By", "type": "last_edited_by"},
    }


def parse_date(text):
    return dateutil.parser.parse(text)

if __name__ == '__main__':
    args = parse_args()
    configure_and_load(args.wunderlist_backup)