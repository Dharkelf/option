# SGHC – Hebelprodukt-Recherche & Optionsstrategie (Briefing)

**Datum:** 13./14. Mai 2026
**User:** Theil (Österreich, Broker: flatex.at)
**Ausgangsfrage:** Mini-Turbo / Knock-Out-Call auf Super Group (SGHC) in Europa handelbar, Hebel 3-5x

---

## 1. Basiswert

| Feld | Wert |
|---|---|
| Name | Super Group (SGHC) Limited |
| Ticker | SGHC (NYSE) |
| ISIN | GG00BMG42V42 |
| WKN | A3DDVD |
| Sitz | Saint Peter Port, Guernsey |
| Geschäft | Online-Sportwetten (Betway) + Online-Casino (Spin) |
| Spot (13.05.2026) | **13,10 USD** (≈ 12,0 EUR bei EUR/USD ~1,09) |
| 52W-Spanne | 8,12 – 14,38 USD |
| Marktkap | ~5,6 Mrd. EUR |
| Implizite/Hist. Vola (30T) | ~44 % p.a. |
| Dividendenrendite | ~2,5 % |
| Earnings-Termine 2026 | Q2: 12.08.2026 · Q3: 11.11.2026 |

---

## 2. Suchergebnis Hebelprodukte in Europa

**Status: kein Hebelprodukt (Knock-Out, Open-End-Turbo, Mini-Future, Faktor) auf SGHC bei den großen europäischen Emittenten gefunden.**

Geprüfte Quellen:
- onvista – Derivate-URL für SGHC leitet auf generischen Finder um (= kein gelistetes Produkt)
- finanzen.net – kein SGHC-Derivat indiziert
- ariva.de, wallstreet-online – nur Aktiendaten
- Vontobel, Société Générale (SG Zertifikate), HSBC, BNP Paribas, Goldman Sachs, Morgan Stanley, UBS – keine SGHC-Produkte indexiert
- Börse Stuttgart Knock-Out-Finder – kein Treffer

**Letzter definitiver Check (live im Broker selbst, durch User):**
- flatex Produktfinder „ivestor Smart Search" – ISIN GG00BMG42V42 eingeben
- Vontobel Zertifikate-Suche – „SGHC"
- SG Zertifikate Turbo-Filter – Basiswert „Super Group"
- Börse Stuttgart Knock-Out-Finder

**Ursache wahrscheinlich:** SGHC ist ein US-gelisteter Mid-Cap aus Guernsey – nicht die typische Schwelle für deutschsprachige Emittenten, die Hebelprodukte auf Retail-nachgefragte Underlyings auflegen.

---

## 3. Hebel-Mathematik – Wunschkalibrierung

Bei Spot 13,10 USD:

| KO-Schwelle (linearer Turbo) | Effektiver Hebel |
|---|---|
| 7 USD (≈7 EUR) | ~2,1x |
| 8 USD | ~2,6x |
| 9 USD | ~3,2x |
| 10 USD | **~4,2x** |
| 11 USD | ~6,2x |

→ Ziel-Korridor 3-5x = **KO zwischen 8,5 und 10,5 USD**.

---

## 4. Plan B – US-Call-Option auf SGHC via flatex

### Voraussetzungen
- Optionshandel bei flatex.at freischalten (WpHG-Erfahrenheitstest „Termingeschäfte")
- Settlement in USD; Standard-Kontraktgröße 100 Aktien (= ~1.310 USD Notional/Kontrakt bei aktuellem Spot)

### Theoretische Kandidaten (Black-Scholes-Modell)

Annahmen: Spot 13,10 USD; IV 0,44; r 5 %; q 2,5 %.

| # | Verfall | Strike | Lage | Mod. Prämie | Delta | Omega (Hebel) |
|---|---|---|---|---|---|---|
| **A** | 21. Aug. 2026 (~100 Tage) | 12 USD | ITM | ~1,80 USD | 0,70 | **~5,1x** |
| **B** | 20. Nov. 2026 (~190 Tage) | 12 USD | ITM | ~2,25 USD | 0,67 | **~4,0x** |
| **C** | 20. Nov. 2026 (~190 Tage) | 14 USD | leicht OTM | ~1,30 USD | 0,49 | **~4,9x** |

### Interpretation
- **A** – schärfster Kurzfrist-Trade, Theta-Verfall ab Mitte Juli stark, ein Earnings-Event (Q2) im Preis
- **B** – „solide" Variante mit Hebel ~4 wie der KO-10-Turbo, aber **ohne KO-Schwelle**; zwei Earnings-Events bis Verfall
- **C** – maximaler Hebel im Korridor, längste Reaktionszeit, Aktie muss klar > 14 USD bis Verfall

### Wichtige Greeks-Begriffe
- **Delta** – Optionspreisänderung pro 1 USD Aktienbewegung (0–1)
- **Omega** = Delta × (Spot / Optionspreis) – effektiver Hebel; vergleichbar mit Turbo-Hebel
- **Theta** – Tagesverfall des Zeitwerts; beschleunigt in den letzten 30-45 Tagen
- **Vega** – Sensitivität auf Vola-Änderung; nach Earnings oft IV-Crush

### Praktische Hinweise
- Bid/Ask-Spread bei Mid-Caps wie SGHC oft 0,05-0,20 USD → **immer Limit-Order**, nie Market
- Open Interest und Volume prüfen vor Kauf (illiquide Strikes meiden)
- Echter Hebel im Live-Markt: Omega = Delta × (Spot / Mid-Preis) selbst nachrechnen
- Kosten flatex.at für US-Optionen: Grundgebühr + Börsenentgelte (in der Regel höher als Turbo-Spread); aktueller Preisaushang prüfen

### Steuer (Österreich, grobe Orientierung)
- 27,5 % KESt wie andere Wertpapierderivate
- flatex.at zieht KESt automatisch ab
- Verluste **nicht** ins Folgejahr vortragbar (Unterschied zu DE)
- Im Einzelfall Steuerberater fragen

---

## 5. Vergleich Turbo vs. Call für SGHC

| Merkmal | Turbo-Call (theoretisch, KO 10) | US-Call Strike 12 (Nov-Verfall) |
|---|---|---|
| Hebel | ~4,2x linear | ~4,0x (Omega), nicht-linear |
| Knock-Out | Ja, bei 10 USD = Totalverlust | Nein |
| Max. Verlust | bezahlte Prämie (KO-Risiko) | bezahlte Prämie |
| Laufzeit | Open-End | Bis Verfall (z. B. 20.11.2026) |
| Theta | minimal (nur Finanzierung) | spürbar, beschleunigt vor Verfall |
| Vega | gering | wichtig (IV-Crush nach Earnings) |
| Verfügbar via flatex | aktuell **kein Produkt** | ja, mit Optionshandel-Freischaltung |
| Spread | typ. eng | mittel-breit (Limit-Order Pflicht) |

---

## 6. Live-Quellen für aktuelle Preise

- onvista Aktie SGHC: https://www.onvista.de/aktien/SPORTS-ENTERTAINMENT-ACQUISITION-CORP-Aktie-GG00BMG42V42
- Nasdaq Option Chain: https://www.nasdaq.com/market-activity/stocks/sghc/option-chain
- MarketBeat Option Chain: https://www.marketbeat.com/stocks/NYSE/SGHC/options/
- Yahoo Finance Options: https://finance.yahoo.com/quote/SGHC/options
- Finviz Volatility & Greeks: https://finviz.com/quote.ashx?t=SGHC
- flatex Produktfinder: https://www.flatex.at/plattformen/produktfinder/
- Cboe 2026 Optionskalender: https://cdn.cboe.com/resources/options/Cboe2026OPTIONSCalendar.pdf

---

## 7. Nächste Schritte (offene Punkte)

1. Im flatex-Depot Live-Bid/Ask zu Kandidaten **A (Aug 12)**, **B (Nov 12)**, **C (Nov 14)** ablesen
2. Echtes Omega = Delta × (Spot / Mid-Preis) berechnen → tatsächlichen Hebel verifizieren
3. Open Interest / Volume prüfen (Liquidität)
4. Falls flatex Optionshandel noch nicht freigeschaltet: Antrag stellen
5. Optional: zweite Suche nach Hebelprodukt im Live-Broker bei den oben genannten Emittenten – falls neu aufgelegt, taucht es dort sofort auf

---

**Disclaimer:** Keine Anlageempfehlung. Alle Preise theoretische Modellwerte oder verzögerte Marktdaten. Hebelprodukte und Optionen haben Totalverlustrisiko. Vor Kauf KID/Basisinformationsblatt bzw. „Options Disclosure Document" lesen. Im Zweifel Steuerberater bzw. unabhängigen Finanzberater konsultieren.
