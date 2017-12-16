# Karol - irc bot inspirowany Największym z Polaków

# Instrukcja
### timer i alarm
Aby ustawić alarm o określonym czasie należy wpisać `notify: HH:MM:SS [wiadomość]`, np:
`notify: 21:37:00 Śpij słodko aniołku`
W efekcie o zadanej godzinie Karol o zadanej godzinie napisze do ciebie podaną wiadomość lub wiadomość domyślną jeśli podałeś tylko godzinę.
Analogicznie działa timer, `timer: HH:MM:SS [wiadomość]`

Można ustawić ograniczoną liczbę notyfikacji w ciągu godziny, a jeśli Karol powie dość lepiej go posłuchać.

### kursy kryptowalut
Po wpisaniu znak dolara i trzyznakowy kod krypotwaluty Karol poda akutalny kurs w dolarach. Przykład:
`$eth`
Jeśli po kodzie kryptowaluty dodamy znak procenta Karol poda zmianę kursu w ciągu ostatniej doby.
`$btc%`
Dodatkowo aby zobaczyć polski kurs po kodzie waluty należy dodać dwukropek:
`$xmr:`

# Wymagania do uruchomienia:
 - Python 3.5+
 - Beautiful Soup
 - dateutils
 - sqlalchemy

# Wymagania do uruchomienia API:
 - Flask 

# TODO:
     - dokładne ciągi jako triggery (opakowane w regexy)
     - wsparcie dla kilku kanałów
     - dodanie jakichś ciekawych tasków (w tym np powiadomienie jeśli waluta osiągnie określony kurs)
     - wyświetlanie listy notyfikacji
     - auto i semiauto kickowanie z powodem z <http://strona0biblii.republika.pl/slowa_b.html> <http://joemonster.org/art/31301>
     - auto rejoin (w tym po ERROR: Closing Link)
     - logi na żądanie 
     - symulacja użytkownika (łańcuch markowa?)
     - odpowiadanie na bezpośrednie zaczepki, szczególnie wulgarne