# Assegnazione automatica OEPAC — vincolo 45h DGC 260/2024

Strumento per l'assegnazione degli alunni con disabilità (servizio OEPAC) agli Organismi accreditati, secondo le Linee Guida approvate con **DGC Roma Capitale n. 260/2024** (Art. 3, commi 5 e 6).

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

1. Caricare il file Excel MESIS (.xlsx) estratto dal sistema regionale
2. (Opzionale) Caricare un file anagrafe plessi per arricchire gli indirizzi
3. Regolare i parametri nella sidebar (soglia ore, iterazioni max)
4. Cliccare "Esegui assegnazione"
5. Scaricare il risultato in formato .xlsx

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

Il file Excel prodotto contiene tre fogli:

1. **Assegnazioni**: una riga per alunno con tutti i dati e l'esito dell'algoritmo
2. **Riepilogo per Plesso x Organismo**: tabella aggregata con ore totali e verifica soglia 45h
3. **Criticità**: solo i record con status diverso da OK, con azione suggerita

## Algoritmo

L'algoritmo applica l'Art. 3, comma 5: ogni Organismo deve raggiungere almeno 45 ore settimanali per plesso (eccezione: plessi con ore totali inferiori a 45). Le riconferme hanno priorità per continuità (Art. 3, comma 6).
