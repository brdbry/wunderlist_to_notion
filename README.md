# wunderlist_to_notion

This script will migrate Wunderlist content into Notion.

It uses the excellent https://github.com/jamalex/notion-py library.

It runs against a **Tasks.json file (generated by a Wunderlist Export)**, which can contain tasks created by/assigned to up to two users (referred to as user_a and user_b in the script).

I wrote it for myself, but with some technical skills you can use it with a few minor tweaks to the script as follows.

To use:

- Export your wunderlist data
- Unzip the export and copy the Tasks.json file somewhere
- Update the top area of the configure_and_load method with:
  - Notion tokens for both users (use same token for both if only one user) - see https://github.com/jamalex/notion-py. If two users you will have to log into Notion from two separate browsers so as to keep both tokens live during the script run (logout expires the token)
  - email address for the main user A
  - The Id or URL of the top level Notion block into which you want to load all your wunderlist data (can copy/paste this from notion.so when on that page)
  - The notion user Ids for the two users. You will need to look at the network requests in devtools when logged in as each user to find these. They are UUIDs
- Edit `run.sh` to specify the location of Tasks.json
- Run: `./run.sh`  
