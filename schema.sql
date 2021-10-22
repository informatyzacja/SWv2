create table votings(
    id integer primary key autoincrement,
    name text,
    options text,
    choice_type text,
    visibility text,
    possible_recipients text,
    sent_to text,
    closes_on_date text
);

create table tokens(
    token text,
    voting_id integer
);
