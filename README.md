# Assegnazione automatica OEPAC — vincolo 45h DGC 260/2024

Strumento per l'assegnazione degli alunni con disabilità (servizio OEPAC) agli Organismi accreditati, secondo le Linee Guida approvate con **DGC Roma Capitale n. 260/2024** (Art. 5, commi 5 e 6).

## Avvio rapido (un click)

**Windows**: doppio click su `avvia.bat`

**Mac / Linux**: doppio click su `avvia.sh` (oppure da terminale: `./avvia.sh`)

Lo script crea automaticamente un ambiente virtuale, installa le dipendenze e apre l'applicazione nel browser.

### Avvio manuale

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Utilizzo

L'interfaccia guida l'operatore in quattro passi, indicati in testa alla pagina:

1. **Carica il file MESIS** (.xlsx estratto dal sistema): l'app riconosce municipio, anno scolastico e data di estrazione
2. **Controlla i dati**: numeri dell'estrazione e tabella "Classificazione scuole" con tipo gestione, ambito e gruppo 45h di ogni plesso (correggibili direttamente in tabella)
3. **Esegui l'assegnazione**: scegliendo in sidebar la modalità **Inizio anno scolastico** oppure **In corso d'anno (finestra di attivazione)**
4. **Scarica i risultati**: report completo, file separati per organismo e lettere PDF

Nella sidebar: parametri economici, file opzionali (anagrafe plessi, elenco scuole comunali) e impostazioni avanzate, tutti raggruppati in sezioni richiudibili con valori predefiniti già corretti.

## Classificazione automatica degli ambiti (Roma)

Con l'opzione **Classificazione automatica ambiti (Roma)** (attiva per impostazione predefinita) il gestionale deriva da solo i gruppi 45h, per qualunque municipio di Roma, anche quando la colonna Ambito del MESIS è incompleta o incoerente:

- **Istituti statali** (codici meccanografici `..AA`/`..EE`/`..MM`): un gruppo per ogni **Istituto Comprensivo** (`IC:<codice istituto>`), anche quando il MESIS li riporta con un ambito numerico anziché "IC";
- **Scuole dell'infanzia comunali** (codici `..1A` di Roma Capitale): gruppi separati da tutto il resto, per **ambito territoriale** (`COM:Ambito <n>`, numerazione cittadina 1–37) quando l'ambito è presente nel file, altrimenti per **municipio** (`COM:Municipio <n>`);
- **Scuole paritarie** (codici `..1A` paritarie, `..1E`, `..1M`): gruppi separati, per ambito territoriale (`PAR:Ambito <n>`) o per municipio (`PAR:Municipio <n>`).

La classificazione usa, in ordine: l'elenco comunali caricato (se presente), il codice meccanografico, le denominazioni ("- COMUNALE", "PARIT…") e la colonna Ambito del MESIS ("n - Paritario" / ambito numerico). Il municipio viene riconosciuto in qualunque formato ("MUNICIPIO ROMA V", "Municipio 7", "XIII", …).

Prima dell'esecuzione, la tabella **Classificazione scuole** mostra ogni plesso con tipo, fonte della classificazione e gruppo derivato: le classificazioni incerte (fonte "presunta") sono segnalate e si possono correggere direttamente nella tabella. In sidebar è possibile caricare un **elenco delle scuole dell'infanzia comunali** (.xlsx/.csv con una colonna di codici meccanografici) per una classificazione certa.

## Assegnazioni in corso d'anno (finestre di attivazione)

Il servizio OEPAC prevede quattro finestre di attivazione durante l'anno (nota Dipartimento Scuola QM/102670/2025): domande entro il 15/07 → attivazione da inizio anno; 16/07–15/10 → da novembre; 16/10–15/01 → da febbraio; 16/01–15/03 → da aprile.

Nella modalità **In corso d'anno** gli alunni già attivati (Organismo Assegnato e Data Attivazione presenti nel MESIS) restano sul loro organismo per continuità e concorrono al calcolo delle 45 ore; l'algoritmo assegna solo le nuove domande della finestra. È possibile indicare una data di riferimento per considerare "già attivati" solo gli alunni attivati fino a quella data.

## File di input

Il file MESIS deve avere:
- Righe 1-7: metadati (ignorati)
- Riga 8: intestazioni colonne
- Riga 9+: dati alunni

## Anagrafe plessi (opzionale)

Per arricchire la colonna "Indirizzo Plesso", caricare un file .xlsx o .csv con le colonne:
- `CODICESCUOLA` (o `codice_meccanografico`): codice meccanografico del plesso
- `INDIRIZZOSCUOLA` (o `indirizzo`): indirizzo

Un'anagrafe utilizzabile è scaricabile dal portale [dati.istruzione.it](https://dati.istruzione.it) nelle sezioni:
- "Anagrafe scuole statali" (rinominare `CODICESCUOLA` → `codice_meccanografico`, `INDIRIZZOSCUOLA` → `indirizzo`)
- "Scuole paritarie" (stesse colonne)

## Output

Il file Excel prodotto contiene i fogli:

1. **Assegnazioni**: una riga per alunno con tutti i dati (compresi Tipo Gestione, Municipio e Gruppo 45h) e l'esito dell'algoritmo
2. **Riepilogo Gruppo**: tabella aggregata per gruppo 45h × Organismo con ore totali e verifica soglia
3. **Riepilogo Economico**: importi per organismo
4. **Criticità**: solo i record con status diverso da OK, con azione suggerita
5. Un foglio per ogni organismo (e in download separato: un .xlsx e una lettera PDF per organismo)

## Algoritmo

L'algoritmo applica l'Art. 5, comma 5 delle Linee Guida: ogni Organismo deve raggiungere di norma almeno 45 ore settimanali per gruppo (eccezione: gruppi con ore totali inferiori a 45). Le riconferme e gli alunni già attivati hanno priorità per continuità (Art. 5, comma 6).
