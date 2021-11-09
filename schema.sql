-- schema for postgres

create table users(
    id serial primary key,
    username text,
    password_hash text
);

create table polls(
    id serial primary key,
    name text,
    options json, -- [ { "name": "Jan Kowalski", "description": "Wydział magii" }, ... ]
    choice_type text,
    visibility text,
    possible_recipients json, -- json array of strings (email addresses)
    sending_out_to json, -- json array of strings (email addresses)
    sent_to json, -- json array of strings (email addresses)
    closes_on_date text,
    mailing_active boolean default false,
    owner_user integer references users(id),
    mail_template text
);
