# Kontrollierte Sprache

Kontrollierte Sprache (Kontrolliertes Deutsch, tekom/DIN 8579-1) ist ein Zusatzflag zu Sachlich oder Formal, kein eigener Modus. Ziel ist Eindeutigkeit und Übersetzbarkeit, nicht Klang: ein Begriff pro Konzept, ein Gedanke pro Satz, feste Anforderungsmodalverben.

## Ziel

Technische Doku, Anleitungen und Spezifikationen brauchen weniger Stimme und mehr Vorhersagbarkeit als Prosa. Kontrolliert schränkt Wortschatz, Satzbau und Modalverben bewusst ein, damit derselbe Sachverhalt immer gleich formuliert wird und maschinell wie menschlich eindeutig lesbar bleibt.

## Aktivierung

Nur auf ausdrücklichen Nutzerwunsch, nicht standardmäßig aus dem Texttyp ableiten. Typische Auslöser: „kontrolliertes Deutsch“, „kontrollierte Sprache“, „regelbasiertes Schreiben“, „DIN 8579-1“, „technische Doku ohne Stil“, explizite Vorgaben zu Terminologie oder Satzlänge. Kombiniert mit Sachlich oder Formal; mit Locker nur auf ausdrücklichen Wunsch, da Modalpartikeln und Nähe-Register den Eindeutigkeitszielen entgegenlaufen.

## Regeln

- **Terminologie:** ein Begriff pro Konzept, keine Synonym-Rotation. Nutzt die Erkennung von Muster 60, aber ohne dessen Häufigkeitsschwelle: Kontrolliert markiert jede Abweichung vom Referenzbegriff, nicht erst ab Cluster.
- **Anforderungsmodalverben:** *muss* (Pflicht), *sollte* (Empfehlung), *kann* (Option), *darf nicht* (Verbot) durchgängig gleich verwenden; siehe Muster 73.
- **Satzkomplexität:** ein Gedanke pro Satz, höchstens eine Nebensatzebene; siehe Muster 74. Steht im Gegensatz zu Muster 51 (Obsessive Parataxe), das genau umgekehrt mehr Subordination verlangt — im Kontrolliert-Modus gilt Muster 74, nicht Muster 51.
- **Aktiv vor Passiv**, wo der Handelnde bekannt ist.
- **Eindeutige Pronomenbezüge:** jedes Pronomen muss ohne Rückfrage auflösbar sein; im Zweifel den Begriff wiederholen statt zu pronominalisieren.
- Muster 45 (Anglizismus-Strukturen) und 58 (Abstrakta-Stapel) gelten unverändert, mit derselben Cluster-Schwelle wie sonst.

## Konflikt mit Rhythmus

Pass 4 verlangt Satzlängen-Varianz (Burstiness) gegen Monotonie (Muster 55). Kontrolliert will das Gegenteil: gleichmäßig kurze, einfach gebaute Sätze sind hier kein Befund, sondern das Ziel. Bei aktivem Kontrolliert-Flag hat diese Vorgabe Vorrang vor Pass 4; Muster 55 wird nicht behandelt, Combing-Gate bleibt aus.

## Output

Bei aktivem Flag ergänzt der Bericht einen kurzen „Kontrolliert“-Block: gefundene Terminologie-Inkonsistenzen, Modalverb-Brüche (Muster 73) und Satzkomplexitäts-Überschreitungen (Muster 74), je mit Kurzzitat. Ohne Befund: „Keine Kontrolliert-Abweichungen.“
