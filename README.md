# Assegnazione automatica OEPAC — vincolo 45h DGC 260/2024

Strumento per l'assegnazione degli alunni con disabilità (servizio OEPAC) agli Organismi accreditati, secondo le Linee Guida approvate con **DGC Roma Capitale n. 260/2024** (Art. 5, commi 5 e 6).

## Installazione su Windows (un click, tutto incluso)

Sul PC Windows, doppio clic su **`Installa-OEPAC.bat`**.

Con un solo clic vengono installati automaticamente **tutti** i componenti necessari:
- **Python** (se non è già presente sul computer, viene installato da solo — tramite winget o scaricando l'installer ufficiale, senza richiedere privilegi di amministratore);
- l'**ambiente dedicato** e tutti i **componenti dell'applicazione** (Streamlit, ecc.);
- i **collegamenti** "Assegnazione OEPAC" sul **Desktop** e nel **Menu Start**.

Al termine il gestionale si avvia da solo. Dalle volte successive basta usare il collegamento sul Desktop (oppure `Avvia-OEPAC.bat`). L'applicazione si apre nel browser; per chiuderla si chiude la finestra nera.

> Per installarlo su più PC: copia l'intera cartella del gestionale su ogni computer (chiavetta USB, cartella condivisa, ecc.) ed esegui `Installa-OEPAC.bat` su ciascuno.

### PC senza internet (installazione offline)

Se i PC di destinazione non hanno accesso a internet (o non è disponibile winget), si prepara **una sola volta** un pacchetto offline:

1. su un PC **con** internet, esegui **`prepara-pacchetto-offline.bat`** (scarica Python e tutti i componenti nella cartella `offline`);
2. copia l'**intera cartella** del gestionale (compresa `offline`) sui PC di destinazione;
3. su ciascun PC esegui `Installa-OEPAC.bat`: rileva il pacchetto offline e installa tutto **senza internet**.

## Avvio su Mac / Linux

Doppio clic su `avvia.sh` (oppure da terminale: `./avvia.sh`). Crea l'ambiente, installa le dipendenze e apre l'applicazione nel browser.

### Avvio manuale (qualsiasi sistema)

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

1. **Assegnazioni**: una riga per alunno con tutti i dati (compresi Tipo Gestione, Municipio e Gruppo 45h) e l'esito dell'algoritmo. Le colonne dell'esito seguono un ordine leggibile come una storia: *Organismo attuale* (dove si trova l'alunno, se già in servizio) → *Preferenze della famiglia (in ordine)* (le scelte espresse: 1ª, 2ª, …) → *Organismo Assegnato* → *Preferenza Soddisfatta*. Così è evidente, ad esempio, quando l'assegnazione onora la prima preferenza della famiglia anche se diversa dall'organismo attuale. Gli alunni **già in servizio** assegnati a un organismo diverso (per preferenza) sono segnalati nella colonna *Note* e contati a video, per un'eventuale valutazione della continuità (non sono errori). Le preferenze della famiglia compaiono solo in questo foglio riservato all'ufficio, non nei file/lettere per le cooperative.
2. **Riepilogo Gruppo**: tabella aggregata per gruppo 45h × Organismo con ore totali e verifica soglia
3. **Riepilogo Economico**: importi per organismo, suddivisi nei due periodi (set-dic e gen-giu) e in totale annuo
4. **Criticità**: solo i record con status diverso da OK, con azione suggerita
5. Un foglio per ogni organismo (e in download separato: un .xlsx e una lettera PDF per organismo)

### Calcolo economico e ripartizione in due periodi

Il periodo annuale della convenzione (35 settimane) è ripartito in due periodi fissi:

- **set-dic**: 14 settimane (da settembre a dicembre)
- **gen-giu**: 21 settimane (da gennaio a giugno)

Ogni report (foglio Assegnazioni, riepilogo economico, fogli e lettere per organismo) riporta gli importi dei due periodi **e** dell'intero anno, sia per singolo alunno sia in aggregato per cooperativa; l'importo annuo coincide sempre con la somma dei due periodi (arrotondati al centesimo, come per una fatturazione separata per periodo).

Gli alunni **attivati in corso d'anno** (in una delle finestre di attivazione) vengono **riparametrati** sulle settimane effettivamente residue: la Data Attivazione del MESIS, confrontata con l'anno scolastico, determina quante delle 14 settimane di set-dic e delle 21 di gen-giu restano da erogare. Le riconferme e le attivazioni di inizio anno mantengono le settimane piene (14 + 21). Le settimane effettive di ciascun periodo sono riportate in colonne dedicate nel report.

## Trasparenza e accesso agli atti

Poiché l'assegnazione è un procedimento automatizzato, il gestionale documenta con un click l'intera sequenza dei passaggi, per ricostruire il «prima e dopo» progressivo utile in caso di accesso agli atti (L. 241/1990) e a evidenza della logica del trattamento (art. 22 Reg. UE 2016/679). Nella sezione **Trasparenza e accesso agli atti** dei risultati sono disponibili:

- **Cronologia del procedimento (.xlsx)**: un foglio di calcolo con il frontespizio (municipio, anno, parametri, riferimenti normativi), la sintesi delle fasi (stato iniziale dal MESIS → assegnazione iniziale → applicazione del vincolo 45h iterazione per iterazione → esito definitivo, con il numero di variazioni per fase), il **diario per alunno** (l'organismo assegnato ad ogni alunno in ciascuna fase, con le celle evidenziate dove c'è stato un cambiamento) e il **registro dei movimenti** (una riga per ogni spostamento, con l'organismo di partenza, quello di destinazione e la motivazione).
- **Verbale del procedimento (.pdf)**: un documento formale che descrive fasi, spostamenti e riferimenti normativi, con spazio per data e firma del responsabile, pronto da allegare a una risposta di accesso agli atti.

Le eventuali **rettifiche manuali** operate dall'ufficio (dalla modalità *Modifica manuale assegnazioni*) vengono aggiunte alla cronologia come fase distinta, così anche gli interventi umani sull'esito automatico restano documentati.

## Algoritmo

L'algoritmo applica l'Art. 5, comma 5 delle Linee Guida: ogni Organismo deve raggiungere di norma almeno 45 ore settimanali per gruppo (eccezione: gruppi con ore totali inferiori a 45). Le riconferme e gli alunni già attivati hanno priorità per continuità (Art. 5, comma 6) e non vengono mai spostati.

La soglia delle 45 ore vale per tutte le scelte: quando la cooperativa scelta da una nuova iscrizione non raggiunge le 45 ore nel gruppo, la domanda viene scalata alla preferenza successiva espressa dalla famiglia, e così via **finché non trova, nell'ordine di preferenza, una cooperativa che raggiunge effettivamente le 45 ore**; se nessuna preferenza le raggiunge, la domanda resta «da assegnare manualmente». Le ore delle riconferme e degli alunni già attivati **concorrono** al raggiungimento delle 45 ore di una cooperativa (continuità dell'operatore già presente), ma la sola presenza di una riconferma **non rende ammissibile** una cooperativa che nel complesso resta sotto le 45 ore.
