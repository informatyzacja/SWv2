-- Administratorzy SW
create table users(
    id serial primary key not null,
    username text not null,

    -- Hash z użyciem bcrypt
    password_hash text not null
);

-- Głosowania
create table polls(
    -- ID odpowiada katalogowi /opt/sw/poll/{id}/
    id serial primary key not null,

    -- Nazwa głosowania: na przykład "Wybory do Rady Wydziału Architektury (W-1)"
    name text not null,

    -- Na co/kogo można głosować - tablica JSON obiektów zawierających "name" i "description"
    -- Przykład: [
    --      { "name": "Jan Kowalski", "description": "Wydział magii" } not null,
    --      { "name": "Adam Nowakowski", "description": "Wydział gier i zabaw" } not null,
    --      ... 
    -- ]
    options json not null,

    -- TODO: ta kolumna nie jest używana.
    -- W założeniu "single-choice" lub "multi-choice"
    choice_type text not null,

    -- TODO: ta kolumna nie jest używana.
    -- W założeniu "private" lub "public"
    visibility text not null,

    -- JSON tablica stringów (adresów email) które zostały wpisane jako głosujący
    -- Przykład: [
    --     '000000@student.pwr.edu.pl',
    --     '000001@student.pwr.edu.pl',
    --     '000002@student.pwr.edu.pl'
    -- ]
    possible_recipients json not null,

    -- JSON tablica stringów (adresów email) które zostały przeniesione do "Do wysłania"
    -- Adresy które znajdują się w tej tablcy znajdują się też w tablicy `possible_recipients` - nie są usuwane
    -- Przykład: [
    --     '000001@student.pwr.edu.pl',
    --     '000002@student.pwr.edu.pl'
    -- ]
    sending_out_to json not null,

    -- JSON tablica stringów (adresów email) do z "Do wysłania" do których sw-mailsender wysłał już wiadomość
    -- Adresy które znajdują się w tej tablcy znajdują się też w tablicach `possible_recipients` oraz `sending_out_to`
    -- Przykład: [
    --     '000002@student.pwr.edu.pl'
    -- ]
    sent_to json not null,

    -- Czas kiedy głosowanie się kończy
    -- Format: "YYYY-MM-DD hh:mm"
    -- Na przykład: "2022-01-01 13:30"
    closes_on_date timestamptz not null,

    -- Czy sw-mailsender wysyła maile z `sending_out_to`?
    mailing_active boolean default false not null,

    -- Administrator który stworzył i zarządza to głosowanie
    owner_user integer references users(id) not null,

    -- Templatka w HTML która zostanie użyta przy wysyłaniu maili.
    -- sw-mailsender.py zamienia {name}, {date_to} i {link} w treści templatki
    mail_template text not null,

    -- Ilu mandatowe jest głosowanie: ile maksymalnie można wybrać osób/opcji przy oddawaniu głosu
    max_choices integer default 1 not null,

    -- Opis głosowania, jeżeli różny od "" wyświetlany przy oddawaniu głosu
    description text default '' not null,

    -- Czy głosowanie jest już zakończone?
    -- Na zakończone głosowania nie można oddawać głosu ani wyświetlać listę opcji/osób/kandydatów
    -- są one także wyświetlane w interfejsie w osobnej kategorii ("Zakończone głosowania")
    closed boolean default false not null,

    -- Jeżeli wartość nie jest NULL, o danej godzinie głosowanie zostanie rozpocząte
    -- (między innymi ustawiając `mailing_active` na true)
    planned_start_sending timestamptz not null
);
