# sw-postfix <img src="../static/logo-with-embedded-font/logo-simple.svg" align="right" height="42px" width="42px">

Serwer [Postfix](http://www.postfix.org/) odbierający wiadomości email z [sw-mailsender](../sw-mailsender) i przekazujący je do `acc.pwr.wroc.pl`.

Pliki **`main.cf`** oraz **`password`** są kopiowane do `/etc/postfix/`.

## Jak zobaczyć kolejkę maili - maile jeszcze nie przekazane do WCSS?

W shellu otwartym przez `vagrant ssh`:

```bash
$ mailq
Mail queue is empty
```

## Interakcje z resztą systemu

![](.images/interactions-sw-postfix.svg)
