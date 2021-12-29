# Opis bazy danych 

System Wyborczy używa PostgreSQL jako bazy danych. Schema znajduje się w pliku [schema.sql](./schema.sql).

## W jaki sposób mogę otworzyć konsolę Postgresa?

```bash
$ sudo -u postgres psql sw
psql (13.5 (Debian 13.5-0+deb11u1))
Type "help" for help.

sw=#
```

## Skrypty

### [`resetdb.sh`](./resetdb.sh)

Skrypt resetuje bazę danych, tworzy tabele od nowa

### [`sw-change-password.py`](./sw-change-password.py)

Skrypt zmienia hasło użytkownika administratora

Przykład użycia (w `vagrant ssh`):

```bash
$ ./sw-change-password.py 'user' 'password'
```

### [`sw-create-user.py`](./sw-create-user.py)

Skrypt tworzy nowego użytkownika administratora z podanym hasłem

Przykład użycia (w `vagrant ssh`):

```bash
$ ./sw-create-user.py 'user' 'password'
```