from pypika import MySQLQuery, Table
from werkzeug.security import generate_password_hash

DEFAULT_TEAMS = [
    "Admin",
    "Frontend",
    "Backend",
    "Mobile",
    "QA",
    "DevOps"
]

TEAM_IDS = {team_name: team_id for team_id, team_name in enumerate(DEFAULT_TEAMS)}

# Username, Password, FirstName, LastName, AdminLevel, TeamID, PfpFilepath
DEFAULT_USERS = [
    # Admin
    ("md", generate_password_hash("mooodeng"), "Moo", "Deng", 2, TEAM_IDS['Admin'], 'pfp/moo.jpg'), 
    # Team Lead
    ("puxp", generate_password_hash("punxsutawney"), "Phil", "Punxsutawney", 1, TEAM_IDS["Mobile"], 'pfp/punxsutawney.jpg'),
    ("simba", generate_password_hash("ifittouchesthesun"), "Simba", "", 1, TEAM_IDS['DevOps'], 'pfp/simba.jpg'),
    ("hachi", generate_password_hash("hachikoko"), "Chūken", "Hachikō", 1, TEAM_IDS["Backend"], 'pfp/hachikō.png'),
    # User
    ("harambe", generate_password_hash("rememberharambe"), "Harambe", "Van Coppenolle", 0, TEAM_IDS["Mobile"], 'pfp/harambe.jpg'),
    ("pomgpriv", generate_password_hash("computeroverride"), "Private", "", 0, TEAM_IDS['Mobile'], 'pfp/private.jpg'),      
    ("crikey", generate_password_hash("saltwatercroc"), "Bindi", "Irwin", 0, TEAM_IDS["DevOps"], 'pfp/bindi.jpg'),
    ("ohana", generate_password_hash("experiment626"), "Stitch", "Pelekai", 0, TEAM_IDS['Backend'], 'pfp/stitch.jpg'),
    ("laika", generate_password_hash("laikaspaceneighbor"), "Laika", "Kudryavka", 0, TEAM_IDS["QA"], 'pfp/laika.jpg'),
    ("wolly", generate_password_hash("mammmmoth"), "Lyuba", "Khudi", 0, None, 'pfp/lyuba.jpg'),
]

USER_IDS = {u[2]: user_id for user_id, u in enumerate(DEFAULT_USERS)}

ISSUE_IDS = {
    "Shadow": 1,
    "ApplePay": 2,
    "OutbackServers": 3,
    "DataLake": 4,
    "Russian": 5,
}

DEFAULT_ISSUES = [
    (ISSUE_IDS["Shadow"], USER_IDS['Phil'], 1, "Shadow Detection"),
    (ISSUE_IDS["ApplePay"], USER_IDS['Phil'], 2, "Apple Pay Vulnerabilities"),
    (ISSUE_IDS["OutbackServers"], USER_IDS['Bindi'], 0,"Outback Servers Bandwidth Consumption"),
    (ISSUE_IDS["DataLake"], USER_IDS['Chūken'], 0, "Data Lake Migration API Ohana Errors?"),
    (ISSUE_IDS["Russian"], USER_IDS['Laika'], 0, "Совместимость с космическим пространством"),
]

DEFAULT_ASSIGNMENTS = [
    (ISSUE_IDS["Shadow"], [USER_IDS['Phil'], USER_IDS['Private'], USER_IDS['Harambe']]),
    (ISSUE_IDS["ApplePay"], [USER_IDS['Phil'], USER_IDS['Private']]),
    (ISSUE_IDS["DataLake"], [USER_IDS['Stitch']]),
]

SUBMIT_STATUS_COMMENT = "SUBMIT_STATUS_UPDATE"
CLOSE_STATUS_COMMENT = 'CLOSE_STATUS_UPDATE'

DEFAULT_COMMENTS = [
    # Shadow Detection Issue 1
    (ISSUE_IDS["Shadow"], USER_IDS['Phil'], "Some mobile users are reporting an erroneous six more weeks of winter with a negative shadow reading after the 1.13 patch. Could we check that out?"),
    (ISSUE_IDS["Shadow"], USER_IDS['Private'], "Sir, I looked into it. It seems like it's mostly affecting users with older devices. Specifically, the update is having compatibility problems with systems before iOS 18 and Android 15."),
    (ISSUE_IDS["Shadow"], USER_IDS['Harambe'], "I submitted a hotfix to revert back to the previous version, but still tackling a permanent fix; @Phil could you give it a look over when you get a chance?"),
    (ISSUE_IDS["Shadow"], USER_IDS['Harambe'], SUBMIT_STATUS_COMMENT),
    # Apple Pay Issue 2
    (ISSUE_IDS["ApplePay"], USER_IDS['Phil'], "The security scan showed a couple minor vulnerabilities for your proposed Apple Pay integration, but I was pretty sure you had everything cleared after this morning's stand-up?"),
    (ISSUE_IDS["ApplePay"], USER_IDS['Private'], "Apologies, I had not sent the most recent scan results, just sent them over now."),
    (ISSUE_IDS["ApplePay"], USER_IDS['Private'], SUBMIT_STATUS_COMMENT),
    (ISSUE_IDS["ApplePay"], USER_IDS['Phil'], "@Private thank you"),
    (ISSUE_IDS["ApplePay"], USER_IDS['Phil'], CLOSE_STATUS_COMMENT),
    # Outback Bandwidth Issue 3
    (ISSUE_IDS['OutbackServers'], USER_IDS['Bindi'], "Got notice that our outback servers are seeing sudden spikes in bandwidth consumption. I know we started sharing the servers with some local companies, but the impact should not be this drastic."),
    (ISSUE_IDS['OutbackServers'], USER_IDS['Simba'], "Thanks for bringing this up @Bindi. That should not be happening. Make sure that the other organizations are primarily on the HPC clusters; everything the lightweight servers touch is our kingdom."),
    # Data Lake Migration Issue 4
    (ISSUE_IDS['DataLake'], USER_IDS['Chūken'], "@Stitch A lot of your API pull requests looks like they're adding new features with an Ohana library? As discussed in the planning meeting, because the data lake itself is already using a lot of new tooling, right now we just want to focus migrating from the previous data warehouse. This means our new data lake query APIs should not have any new dependencies that our old APIs did not have. "),
    (ISSUE_IDS['DataLake'], USER_IDS['Stitch'], "Ohana means family and family means Stitch thinks we should use migration as an opportunity to address some inefficiencies of the old data query APIs."),
    (ISSUE_IDS['DataLake'], USER_IDS['Chūken'], "I completely understand your concern, but right now as a team we're focused on migration, which is taking up a lot of resources and delaying services for our users. Right now, I think it's best if we diligently work towards making sure the migration goes smoothly. Afterwards we can focus on addressing inefficiencies."),
    (ISSUE_IDS['DataLake'], USER_IDS['Chūken'], "Additionally, an explanation of the Ohana library more comprehensive explanation than “it means family” would be appreciated."),
    # Russian Issue 5
    (ISSUE_IDS['Russian'], USER_IDS['Laika'], "Я тестировал этот продукт в космосе. оно сломалось."),
]

DEFAULT_ISSUE_TEAMS = [
    (ISSUE_IDS["Shadow"], TEAM_IDS["Mobile"]),    
    (ISSUE_IDS["ApplePay"], TEAM_IDS["Mobile"]),
    (ISSUE_IDS["OutbackServers"], TEAM_IDS["DevOps"]),
    (ISSUE_IDS["DataLake"], TEAM_IDS["Backend"]),
    (ISSUE_IDS["Russian"], TEAM_IDS["QA"])    
]

if __name__ == '__main__':
    team = Table('team')
    user = Table('user')
    issue = Table('issue')
    comment = Table('comment')
    assignment = Table('assignment')
    issue_team = Table('issue_team')

    queries = []
    queries.append(MySQLQuery.into(team).columns('team_name', 'id').insert(*TEAM_IDS.items())) 
    queries.append(MySQLQuery.into(user).columns('username', 'password', 'first_name', 'last_name', 'admin_level', 'team_id', 'pfp_filename').insert(*DEFAULT_USERS))
   
    queries.append(MySQLQuery.into(issue).columns('id', 'author_id', 'progress', 'title').insert(*DEFAULT_ISSUES))
    queries.append(MySQLQuery.into(comment).columns('issue_id', 'author_id', 'content').insert(*DEFAULT_COMMENTS))
    for issue_id, assignees in DEFAULT_ASSIGNMENTS:
        for a_id in assignees:
            queries.append(MySQLQuery.into(assignment).columns('issue_id', 'assignee_id').insert((issue_id, a_id)))
    queries.append(MySQLQuery.into(issue_team).columns('issue_id', 'team_id').insert(*DEFAULT_ISSUE_TEAMS))

    with open("02_data.sql", "w") as f:
        for q in queries:
            print(f"{q.get_sql()};", file=f)