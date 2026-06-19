"""
Assegnazione automatica OEPAC — vincolo 45h DGC 260/2024

Strumento per l'assegnazione degli alunni con disabilità (servizio OEPAC)
agli Organismi accreditati, secondo le Linee Guida approvate con
DGC Roma Capitale n. 260/2024 (Art. 3, commi 5 e 6).
"""

import datetime
import io
import re

import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def normalizza_nome(nome: str) -> str:
    if not isinstance(nome, str):
        return ""
    return re.sub(r"\s+", " ", nome.strip()).casefold()


def nomi_uguali(a: str, b: str) -> bool:
    return normalizza_nome(a) == normalizza_nome(b)



def parse_data_nascita(val) -> datetime.date | None:
    if isinstance(val, datetime.datetime):
        return val.date()
    if isinstance(val, datetime.date):
        return val
    if pd.isna(val):
        return None
    s = str(val).strip().split(" ")[0]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def calcola_eta(data_nascita: datetime.date | None) -> int | None:
    if data_nascita is None:
        return None
    oggi = datetime.date.today()
    eta = oggi.year - data_nascita.year
    if (oggi.month, oggi.day) < (data_nascita.month, data_nascita.day):
        eta -= 1
    return eta


def deriva_grado(codice_mecc_plesso: str, ambito: str = "") -> str:
    if not isinstance(codice_mecc_plesso, str) or len(codice_mecc_plesso) < 4:
        return "N/D"
    prefix = codice_mecc_plesso[2:4].upper()
    ambito_up = ambito.upper().strip() if isinstance(ambito, str) else ""
    is_paritario = "PARITARIO" in ambito_up or "PARIT" in ambito_up

    if prefix == "AA":
        return "Infanzia statale"
    if prefix == "EE":
        return "Primaria statale"
    if prefix == "MM":
        return "Sec. I grado statale"
    if prefix == "1A":
        if is_paritario:
            return "Infanzia paritaria"
        return "Infanzia comunale"
    if prefix == "1E":
        return "Primaria paritaria" if is_paritario else "Primaria"
    if prefix == "1M":
        return "Sec. I grado paritaria" if is_paritario else "Sec. I grado"
    return "N/D"


def parse_preferenze(testo: str) -> list[str]:
    if not isinstance(testo, str) or not testo.strip():
        return []
    righe = testo.split("\n")
    preferenze = []
    for riga in righe:
        riga = riga.strip()
        if not riga:
            continue
        if re.match(r"^Domanda\s+\d+\s*:", riga):
            continue
        preferenze.append(riga)
    return preferenze


# ---------------------------------------------------------------------------
# Column mapping — maps spec names to actual Excel header variations
# ---------------------------------------------------------------------------

COLUMN_MAP = [
    ("codice_iscrizione", ["Codice"]),
    ("stato", ["Stato"]),
    ("tipo", ["Tipo"]),
    ("municipio", ["Municipio"]),
    ("cognome", ["Cognome"]),
    ("nome", ["Nome"]),
    ("data_nascita", ["Data Nascita", "Data di Nascita"]),
    ("codice_mecc_istituto", ["Codice Meccanografico Istituto"]),
    ("istituto", ["Istituto"]),
    ("codice_mecc_plesso", ["Codice Meccanografico Plesso"]),
    ("plesso", ["Plesso"]),
    ("classe", ["Classe"]),
    ("sezione", ["Sezione"]),
    ("ambito", ["Ambito"]),
    ("ore_richieste", ["Ore Richieste"]),
    ("ore_assegnate", ["Ore Assegnate"]),
    ("codice_utente", ["UTENTE"]),
    ("organismo_assegnato", ["Organismo Assegnato"]),
    ("enti_erogatori_scelti", ["Enti Erogatori scelti", "Enti Erogatori Scelti"]),
    ("data_attivazione", ["Data Attivazione"]),
    ("data_rinuncia", ["Data Rinuncia/Sospensione", "Data Rinuncia"]),
]


def map_columns(df: pd.DataFrame) -> dict[str, str]:
    headers = list(df.columns)
    headers_lower = [h.strip().lower() if isinstance(h, str) else "" for h in headers]
    used: set[int] = set()
    mapping: dict[str, str] = {}

    for key, candidates in COLUMN_MAP:
        for cand in candidates:
            cl = cand.strip().lower()
            for i, h in enumerate(headers_lower):
                if i in used:
                    continue
                if cl == h:
                    mapping[key] = headers[i]
                    used.add(i)
                    break
            if key in mapping:
                break

    for key, candidates in COLUMN_MAP:
        if key in mapping:
            continue
        for cand in candidates:
            cl = cand.strip().lower()
            for i, h in enumerate(headers_lower):
                if i in used:
                    continue
                if cl in h:
                    mapping[key] = headers[i]
                    used.add(i)
                    break
            if key in mapping:
                break

    return mapping


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def carica_dati(file_bytes: bytes) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
    errors = []
    df_raw = pd.read_excel(
        io.BytesIO(file_bytes),
        sheet_name=0,
        header=None,
        dtype=str,
    )

    header_row_idx = 7
    if df_raw.shape[0] <= header_row_idx:
        errors.append(
            f"Il file ha solo {df_raw.shape[0]} righe — mi aspetto almeno 9 "
            "(7 di metadati + 1 intestazione + dati)."
        )
        return pd.DataFrame(), {}, errors

    raw_headers = [
        re.sub(r"\s+", " ", str(v).strip()) if pd.notna(v) else f"Col_{i}"
        for i, v in enumerate(df_raw.iloc[header_row_idx])
    ]
    seen: dict[str, int] = {}
    headers = []
    for h in raw_headers:
        if h in seen:
            seen[h] += 1
            headers.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            headers.append(h)

    df = df_raw.iloc[header_row_idx + 1 :].copy()
    df.columns = headers
    df.reset_index(drop=True, inplace=True)

    col_map = map_columns(df)

    required = [
        "codice_iscrizione", "stato", "tipo", "cognome", "nome",
        "codice_mecc_plesso", "ore_assegnate",
    ]
    col_map_lookup = dict(COLUMN_MAP)
    for req in required:
        if req not in col_map:
            errors.append(
                f"Colonna obbligatoria non trovata: {req} "
                f"(cercate: {col_map_lookup.get(req, [])})"
            )

    return df, col_map, errors


# ---------------------------------------------------------------------------
# Algorithm
# ---------------------------------------------------------------------------

def esegui_assegnazione(
    df: pd.DataFrame,
    col_map: dict[str, str],
    soglia_ore: int = 45,
    max_iter: int = 50,
):

    log = []
    stats = {
        "totale_alunni": 0,
        "riconferme": 0,
        "nuove_iscrizioni": 0,
        "criticita": 0,
        "spostamenti": 0,
        "iterazioni": 0,
    }

    def col(key):
        return col_map.get(key)

    stato_col = col("stato")
    rinuncia_col = col("data_rinuncia")
    tipo_col = col("tipo")
    plesso_col = col("codice_mecc_plesso")
    ore_col = col("ore_assegnate")
    org_col = col("organismo_assegnato")
    enti_col = col("enti_erogatori_scelti")
    codice_col = col("codice_iscrizione")

    mask = df[stato_col].str.strip().str.upper() == "ATTIVA"
    if rinuncia_col:
        mask &= df[rinuncia_col].isna() | (df[rinuncia_col].str.strip() == "")
    df_work = df.loc[mask].copy()
    df_work.reset_index(drop=True, inplace=True)

    empty_result_cols = [
        "Codice Iscrizione", "Tipo", "Cognome", "Nome", "Data Nascita",
        "Età", "Codice Meccanografico Istituto", "Istituto",
        "Codice Meccanografico Plesso", "Plesso", "Indirizzo Plesso",
        "Grado Scolastico", "Classe", "Sezione", "Ambito", "Gruppo 45h",
        "Ore Richieste", "Ore Assegnate", "Organismo Pre-esistente",
        "Organismo Assegnato dall'Algoritmo", "Preferenza Soddisfatta",
        "Data Attivazione", "Status", "Note",
    ]
    if len(df_work) == 0:
        df_empty = pd.DataFrame(columns=empty_result_cols)
        df_riep_empty = pd.DataFrame(columns=[
            "Gruppo 45h", "Tipo gruppo", "Descrizione", "Ambito",
            "N. plessi", "Organismo", "N. alunni assegnati",
            "Ore totali settimanali org.", "Ore totali del gruppo", "Soglia 45h",
        ])
        df_crit_empty = pd.DataFrame(columns=empty_result_cols + ["Azione suggerita"])
        log.append("Nessun alunno con Stato=ATTIVA trovato.")
        return df_empty, df_riep_empty, df_crit_empty, log, stats, {}

    ambito_col = col("ambito")
    ist_col = col("codice_mecc_istituto")

    df_work["_ore"] = pd.to_numeric(df_work[ore_col], errors="coerce").fillna(0)
    df_work["_tipo_norm"] = df_work[tipo_col].str.strip().str.upper().fillna("")
    df_work["_plesso"] = df_work[plesso_col].str.strip().fillna("")
    df_work["_org_orig"] = df_work[org_col].str.strip().fillna("") if org_col else ""
    df_work["_codice"] = df_work[codice_col].str.strip().fillna("")
    df_work["_ambito"] = df_work[ambito_col].str.strip().fillna("") if ambito_col else ""
    df_work["_istituto"] = df_work[ist_col].str.strip().fillna("") if ist_col else ""

    def calcola_gruppo_45h(row) -> str:
        ambito = row["_ambito"]
        if ambito.upper() == "IC":
            return f"IC:{row['_istituto']}"
        if ambito:
            return f"AMB:{ambito}"
        return f"PLESSO:{row['_plesso']}"

    df_work["_gruppo"] = df_work.apply(calcola_gruppo_45h, axis=1)

    nome_registro: dict[str, str] = {}

    def registra_nome(nome: str):
        if isinstance(nome, str) and nome.strip():
            nome_registro[normalizza_nome(nome)] = nome.strip()

    for _, row in df_work.iterrows():
        if isinstance(row.get("_org_orig"), str) and row["_org_orig"]:
            registra_nome(row["_org_orig"])
        if enti_col and isinstance(row.get(enti_col), str):
            for pref in parse_preferenze(row[enti_col]):
                registra_nome(pref)

    df_work["_preferenze"] = df_work[enti_col].apply(parse_preferenze) if enti_col else [[] for _ in range(len(df_work))]

    is_riconferma = df_work["_tipo_norm"] == "RICONFERMA"
    is_nuova = df_work["_tipo_norm"] == "NUOVA ISCRIZIONE"
    is_altro = ~is_riconferma & ~is_nuova

    stats["totale_alunni"] = len(df_work)
    stats["riconferme"] = int(is_riconferma.sum())
    stats["nuove_iscrizioni"] = int(is_nuova.sum())

    df_work["_assegnato"] = ""
    df_work["_pref_idx"] = 0
    df_work["_status"] = ""
    df_work["_note"] = ""
    df_work["_pref_soddisfatta"] = ""

    for idx in df_work.index[is_altro]:
        tipo_orig = df_work.at[idx, tipo_col] if tipo_col else "?"
        df_work.at[idx, "_status"] = "Da assegnare manualmente"
        df_work.at[idx, "_note"] = f"Tipo iscrizione non riconosciuto: '{tipo_orig}'"
        df_work.at[idx, "_pref_soddisfatta"] = "Non assegnato"

    for idx in df_work.index[is_riconferma]:
        org = df_work.at[idx, "_org_orig"]
        if isinstance(org, str) and org.strip():
            df_work.at[idx, "_assegnato"] = org.strip()
            df_work.at[idx, "_pref_soddisfatta"] = "Riconferma"
            df_work.at[idx, "_status"] = "OK"
        else:
            df_work.at[idx, "_status"] = "OK"
            df_work.at[idx, "_pref_soddisfatta"] = "Riconferma"
            df_work.at[idx, "_note"] = "Riconferma senza organismo pre-esistente"

    nuove_idx = sorted(
        df_work.index[is_nuova].tolist(),
        key=lambda i: df_work.at[i, "_codice"],
    )

    for idx in nuove_idx:
        prefs = df_work.at[idx, "_preferenze"]
        if not prefs:
            df_work.at[idx, "_status"] = "Preferenze non espresse"
            df_work.at[idx, "_note"] = "Preferenze non espresse — richiedere alla famiglia"
            df_work.at[idx, "_pref_soddisfatta"] = "Non assegnato"
            continue
        df_work.at[idx, "_assegnato"] = prefs[0]
        df_work.at[idx, "_pref_idx"] = 0

    gruppi = df_work["_gruppo"].unique()
    ore_totali_gruppo: dict[str, float] = {}
    for g in gruppi:
        ore_totali_gruppo[g] = df_work.loc[df_work["_gruppo"] == g, "_ore"].sum()

    non_viable_set: dict[str, set[str]] = {g: set() for g in gruppi}

    for iteration in range(1, max_iter + 1):
        spostamenti = 0

        ore_per_coop: dict[str, dict[str, float]] = {g: {} for g in gruppi}
        for idx in df_work.index:
            if df_work.at[idx, "_status"] in (
                "Preferenze non espresse",
                "Da assegnare manualmente",
            ):
                continue
            g = df_work.at[idx, "_gruppo"]
            org = df_work.at[idx, "_assegnato"]
            if not org:
                continue
            org_n = normalizza_nome(org)
            ore_per_coop[g][org_n] = ore_per_coop[g].get(org_n, 0) + df_work.at[idx, "_ore"]

        riconferme_per_coop: dict[str, set[str]] = {g: set() for g in gruppi}
        for idx in df_work.index[is_riconferma]:
            g = df_work.at[idx, "_gruppo"]
            org = df_work.at[idx, "_assegnato"]
            if org:
                riconferme_per_coop[g].add(normalizza_nome(org))

        nuovi_non_viable = []
        for g in gruppi:
            soglia_attiva = ore_totali_gruppo[g] >= soglia_ore
            if not soglia_attiva:
                continue
            for org_n, ore in ore_per_coop[g].items():
                if ore < soglia_ore and org_n not in riconferme_per_coop[g]:
                    nuovi_non_viable.append((g, org_n))

        if not nuovi_non_viable:
            log.append(f"Iterazione {iteration}: nessuno spostamento — convergenza raggiunta.")
            stats["iterazioni"] = iteration
            break

        for g, org_n in nuovi_non_viable:
            non_viable_set[g].add(org_n)

        for idx in nuove_idx:
            if df_work.at[idx, "_status"] in (
                "Preferenze non espresse",
                "Da assegnare manualmente",
            ):
                continue
            g = df_work.at[idx, "_gruppo"]
            org = df_work.at[idx, "_assegnato"]
            if not org:
                continue
            org_n = normalizza_nome(org)
            if (g, org_n) not in [(gg, oo) for gg, oo in nuovi_non_viable]:
                continue

            prefs = df_work.at[idx, "_preferenze"]
            trovato = False
            for pi in range(len(prefs)):
                pref_n = normalizza_nome(prefs[pi])
                if pref_n not in non_viable_set[g]:
                    df_work.at[idx, "_assegnato"] = prefs[pi]
                    df_work.at[idx, "_pref_idx"] = pi
                    spostamenti += 1
                    trovato = True
                    break

            if not trovato:
                df_work.at[idx, "_assegnato"] = ""
                df_work.at[idx, "_status"] = "Da assegnare manualmente"
                df_work.at[idx, "_note"] = (
                    "Tutte le preferenze espresse risultano sotto soglia "
                    f"{soglia_ore}h nel plesso — assegnazione manuale necessaria"
                )
                df_work.at[idx, "_pref_soddisfatta"] = "Non assegnato"
                spostamenti += 1

        log.append(
            f"Iterazione {iteration}: {spostamenti} spostamenti, "
            f"{sum(1 for i in nuove_idx if df_work.at[i, '_status'] == 'Da assegnare manualmente')} "
            f"casi non risolti."
        )
        stats["spostamenti"] += spostamenti
        stats["iterazioni"] = iteration

        if spostamenti == 0:
            break
    else:
        log.append(f"Raggiunto limite massimo di {max_iter} iterazioni.")

    for idx in nuove_idx:
        if df_work.at[idx, "_status"] in ("Preferenze non espresse", "Da assegnare manualmente"):
            continue
        prefs = df_work.at[idx, "_preferenze"]
        pi = df_work.at[idx, "_pref_idx"]
        df_work.at[idx, "_pref_soddisfatta"] = f"{pi + 1}ª"
        df_work.at[idx, "_status"] = "OK"

    ore_per_coop_final: dict[str, dict[str, float]] = {g: {} for g in gruppi}
    for idx in df_work.index:
        if df_work.at[idx, "_status"] in ("Preferenze non espresse", "Da assegnare manualmente"):
            continue
        g = df_work.at[idx, "_gruppo"]
        org = df_work.at[idx, "_assegnato"]
        if not org:
            continue
        org_n = normalizza_nome(org)
        ore_per_coop_final[g][org_n] = (
            ore_per_coop_final[g].get(org_n, 0) + df_work.at[idx, "_ore"]
        )

    for idx in df_work.index[is_riconferma]:
        g = df_work.at[idx, "_gruppo"]
        org = df_work.at[idx, "_assegnato"]
        if not org:
            continue
        org_n = normalizza_nome(org)
        soglia_attiva = ore_totali_gruppo.get(g, 0) >= soglia_ore
        ore_coop = ore_per_coop_final.get(g, {}).get(org_n, 0)
        if soglia_attiva and ore_coop < soglia_ore:
            df_work.at[idx, "_status"] = "Riconferma sotto soglia"
            df_work.at[idx, "_note"] = (
                f"Riconferma sotto soglia {soglia_ore}h — "
                "verificare con la Direzione Socio-Educativa municipale"
            )

    stats["criticita"] = int(
        (df_work["_status"] != "OK").sum()
    )

    dn_col = col("data_nascita")
    plesso_nome_col = col("plesso")
    istituto_col = col("istituto")
    codice_mecc_ist_col = col("codice_mecc_istituto")
    classe_col = col("classe")
    sezione_col = col("sezione")
    ambito_col = col("ambito")
    ore_rich_col = col("ore_richieste")
    data_att_col = col("data_attivazione")
    municipio_col = col("municipio")

    result_rows = []
    for idx in df_work.index:
        dn = parse_data_nascita(df_work.at[idx, dn_col]) if dn_col else None
        eta = calcola_eta(dn)
        plesso_code = df_work.at[idx, "_plesso"]
        ambito_val = df_work.at[idx, "_ambito"]
        grado = deriva_grado(plesso_code, ambito_val)

        dn_str = dn.strftime("%d/%m/%Y") if dn else ""

        result_rows.append({
            "Codice Iscrizione": df_work.at[idx, "_codice"],
            "Tipo": df_work.at[idx, tipo_col] if tipo_col else "",
            "Cognome": df_work.at[idx, col("cognome")] if col("cognome") else "",
            "Nome": df_work.at[idx, col("nome")] if col("nome") else "",
            "Data Nascita": dn_str,
            "Età": eta if eta is not None else "",
            "Codice Meccanografico Istituto": (
                df_work.at[idx, codice_mecc_ist_col] if codice_mecc_ist_col else ""
            ),
            "Istituto": df_work.at[idx, istituto_col] if istituto_col else "",
            "Codice Meccanografico Plesso": plesso_code,
            "Plesso": df_work.at[idx, plesso_nome_col] if plesso_nome_col else "",
            "Indirizzo Plesso": "",
            "Grado Scolastico": grado,
            "Classe": df_work.at[idx, classe_col] if classe_col else "",
            "Sezione": df_work.at[idx, sezione_col] if sezione_col else "",
            "Ambito": df_work.at[idx, "_ambito"],
            "Gruppo 45h": df_work.at[idx, "_gruppo"],
            "Ore Richieste": df_work.at[idx, ore_rich_col] if ore_rich_col else "",
            "Ore Assegnate": df_work.at[idx, "_ore"],
            "Organismo Pre-esistente": df_work.at[idx, "_org_orig"] if isinstance(df_work.at[idx, "_org_orig"], str) else "",
            "Organismo Assegnato dall'Algoritmo": df_work.at[idx, "_assegnato"],
            "Preferenza Soddisfatta": df_work.at[idx, "_pref_soddisfatta"],
            "Data Attivazione": df_work.at[idx, data_att_col] if data_att_col else "",
            "Status": df_work.at[idx, "_status"],
            "Note": df_work.at[idx, "_note"],
        })

    df_result = pd.DataFrame(result_rows)

    sort_cols = [
        c for c in [
            "Codice Meccanografico Istituto",
            "Codice Meccanografico Plesso",
            "Classe",
            "Sezione",
            "Cognome",
            "Nome",
        ]
        if c in df_result.columns
    ]
    if sort_cols:
        if "Classe" in df_result.columns:
            df_result["_classe_sort"] = pd.to_numeric(
                df_result["Classe"], errors="coerce"
            ).fillna(float("inf"))
            real_sort = [
                "_classe_sort" if c == "Classe" else c for c in sort_cols
            ]
            df_result.sort_values(real_sort, inplace=True, ignore_index=True)
            df_result.drop(columns=["_classe_sort"], inplace=True)
        else:
            df_result.sort_values(sort_cols, inplace=True, ignore_index=True)

    df_riepilogo = costruisci_riepilogo_gruppo(df_result, soglia_ore)
    df_criticita = costruisci_criticita(df_result)

    return df_result, df_riepilogo, df_criticita, log, stats, nome_registro


def costruisci_riepilogo_gruppo(df_result, soglia_ore=45):
    """Costruisce il riepilogo per (Gruppo 45h x Organismo) dal DataFrame assegnazioni."""
    ORG = "Organismo Assegnato dall'Algoritmo"
    riepilogo_rows = []
    gruppi_result = df_result["Gruppo 45h"].unique()
    for grp in sorted(g for g in gruppi_result if g):
        df_g = df_result.loc[df_result["Gruppo 45h"] == grp]
        ore_tot_g = df_g["Ore Assegnate"].sum()

        if grp.startswith("IC:"):
            tipo_gruppo = "IC"
            desc_gruppo = df_g["Istituto"].iloc[0] if "Istituto" in df_g.columns else ""
            n_plessi = df_g["Codice Meccanografico Plesso"].nunique()
        elif grp.startswith("AMB:"):
            amb_val = grp.replace("AMB:", "")
            tipo_gruppo = "Paritario" if "Paritario" in amb_val else "Comunale"
            nomi = sorted(df_g.drop_duplicates("Codice Meccanografico Istituto")["Istituto"].unique())
            desc_gruppo = ", ".join(nomi[:3]) + (f" (+{len(nomi)-3})" if len(nomi) > 3 else "")
            n_plessi = df_g["Codice Meccanografico Plesso"].nunique()
        else:
            tipo_gruppo = ""
            desc_gruppo = df_g["Plesso"].iloc[0] if "Plesso" in df_g.columns else ""
            n_plessi = 1

        for org in sorted(o for o in df_g[ORG].unique() if o):
            mask_o = df_g[ORG] == org
            ore_org = df_g.loc[mask_o, "Ore Assegnate"].sum()
            if ore_tot_g < soglia_ore:
                soglia_str = "N/A (gruppo sotto 45h totali)"
            elif ore_org >= soglia_ore:
                soglia_str = "Raggiunta"
            else:
                soglia_str = "Non raggiunta"
            riepilogo_rows.append({
                "Gruppo 45h": grp,
                "Tipo gruppo": tipo_gruppo,
                "Descrizione": desc_gruppo,
                "Ambito": df_g["Ambito"].iloc[0],
                "N. plessi": n_plessi,
                "Organismo": org,
                "N. alunni assegnati": int(mask_o.sum()),
                "Ore totali settimanali org.": ore_org,
                "Ore totali del gruppo": ore_tot_g,
                "Soglia 45h": soglia_str,
            })
    return pd.DataFrame(riepilogo_rows)


def costruisci_criticita(df_result):
    """Estrae i record critici (Status != OK) con azione suggerita."""
    df_criticita = df_result.loc[df_result["Status"] != "OK"].copy()
    azioni = {
        "Preferenze non espresse": "Contattare la famiglia per acquisire le preferenze",
        "Da assegnare manualmente": "Spostamento manuale necessario",
        "Riconferma sotto soglia": "Inoltrare segnalazione formale alla Direzione Socio-Educativa",
    }
    if not df_criticita.empty:
        df_criticita["Azione suggerita"] = df_criticita["Status"].map(azioni).fillna("")
    else:
        df_criticita["Azione suggerita"] = []
    return df_criticita


def arricchisci_indirizzi(df_result: pd.DataFrame, file_bytes: bytes, filename: str = "") -> pd.DataFrame:
    try:
        if filename.lower().endswith(".csv"):
            df_ana = pd.read_csv(io.BytesIO(file_bytes), dtype=str)
        else:
            try:
                df_ana = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
            except Exception:
                df_ana = pd.read_csv(io.BytesIO(file_bytes), dtype=str)
        cols_lower = {c.strip().lower(): c for c in df_ana.columns}

        cod_col = None
        ind_col = None
        for k, v in cols_lower.items():
            if "codice" in k and "meccanografico" in k:
                cod_col = v
            elif "codice_meccanografico" in k:
                cod_col = v
            elif k == "codicescuola":
                cod_col = v
        for k, v in cols_lower.items():
            if "indirizzo" in k:
                ind_col = v

        if cod_col and ind_col:
            lookup = dict(
                zip(
                    df_ana[cod_col].str.strip(),
                    df_ana[ind_col].str.strip(),
                )
            )
            df_result["Indirizzo Plesso"] = df_result[
                "Codice Meccanografico Plesso"
            ].map(lookup).fillna("")
    except Exception:
        pass
    return df_result


# ---------------------------------------------------------------------------
# Economic calculations (shared by Excel, PDF, dashboard)
# ---------------------------------------------------------------------------

def calcola_colonne_economiche(
    df, n_settimane=35, perc_decurtazione=11.0, costo_orario=24.07, aliquota_iva=5.0
):
    """Aggiunge le colonne economiche derivate al DataFrame delle assegnazioni."""
    coeff_netto = 1 - perc_decurtazione / 100
    coeff_iva = aliquota_iva / 100
    ore_sett = pd.to_numeric(df["Ore Assegnate"], errors="coerce").fillna(0)
    ore_annuali = ore_sett * n_settimane
    decurtazione = ore_annuali * (perc_decurtazione / 100)
    ore_nette = ore_annuali * coeff_netto
    imponibile = ore_nette * costo_orario
    iva = imponibile * coeff_iva
    totale = imponibile + iva
    out = df.copy()
    out["Ore annuali lorde"] = ore_annuali
    out[f"Decurtazione {perc_decurtazione:.0f}%"] = decurtazione
    out["Ore annuali nette"] = ore_nette
    out["Imponibile (EUR)"] = imponibile.round(2)
    out[f"IVA {aliquota_iva:.0f}% (EUR)"] = iva.round(2)
    out["Totale (EUR)"] = totale.round(2)
    return out


def calcola_riepilogo_economico(
    df_eco, n_settimane=35, perc_decurtazione=11.0, costo_orario=24.07, aliquota_iva=5.0
):
    """Costruisce il riepilogo economico aggregato per organismo."""
    ORG = "Organismo Assegnato dall'Algoritmo"
    organismi = sorted([o for o in df_eco[ORG].unique() if o])
    iva_col = f"IVA {aliquota_iva:.0f}% (EUR)"
    rows = []
    for org in organismi:
        df_o = df_eco.loc[df_eco[ORG] == org]
        ore_lorde = df_o["Ore annuali lorde"].sum()
        ore_nette = df_o["Ore annuali nette"].sum()
        rows.append({
            "Organismo": org,
            "N. alunni": len(df_o),
            "Ore sett. totali": df_o["Ore Assegnate"].sum(),
            f"Ore annuali lorde ({n_settimane} sett.)": ore_lorde,
            f"Decurtazione {perc_decurtazione:.0f}%": ore_lorde - ore_nette,
            "Ore annuali nette": ore_nette,
            "Costo orario": costo_orario,
            "Imponibile (EUR)": round(df_o["Imponibile (EUR)"].sum(), 2),
            iva_col: round(df_o[iva_col].sum(), 2),
            "Totale (EUR)": round(df_o["Totale (EUR)"].sum(), 2),
        })
    return pd.DataFrame(rows)


def colonne_coop(perc_decurtazione=11.0, aliquota_iva=5.0):
    """Colonne da mostrare nei fogli/lettere per cooperativa."""
    return [
        "Codice Iscrizione", "Tipo", "Cognome", "Nome", "Data Nascita", "Età",
        "Codice Meccanografico Istituto", "Istituto",
        "Codice Meccanografico Plesso", "Plesso", "Grado Scolastico",
        "Classe", "Sezione", "Ambito", "Gruppo 45h",
        "Ore Assegnate", "Ore annuali lorde",
        f"Decurtazione {perc_decurtazione:.0f}%", "Ore annuali nette",
        "Imponibile (EUR)", f"IVA {aliquota_iva:.0f}% (EUR)", "Totale (EUR)",
        "Preferenza Soddisfatta", "Status",
    ]


# ---------------------------------------------------------------------------
# Excel output with formatting
# ---------------------------------------------------------------------------

def genera_excel(
    df_assegnazioni, df_riepilogo, df_criticita,
    n_settimane: int = 35,
    perc_decurtazione: float = 11.0,
    costo_orario: float = 24.07,
    aliquota_iva: float = 5.0,
) -> bytes:
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    BRAND = "1F4E79"
    BRAND_LIGHT = "D6E4F0"
    ACCENT = "2E75B6"
    WHITE = "FFFFFF"
    ZEBRA = "F2F7FB"

    HDR_FONT = Font(bold=True, color=WHITE, size=10)
    HDR_FILL = PatternFill(start_color=BRAND, end_color=BRAND, fill_type="solid")
    TITLE_FONT = Font(bold=True, size=14, color=BRAND)
    SUBTITLE_FONT = Font(bold=True, size=11, color=ACCENT)
    PARAM_FONT = Font(size=10, color="444444")
    TOTAL_FONT = Font(bold=True, size=10, color=BRAND)
    TOTAL_FILL = PatternFill(start_color=BRAND_LIGHT, end_color=BRAND_LIGHT, fill_type="solid")
    ZEBRA_FILL = PatternFill(start_color=ZEBRA, end_color=ZEBRA, fill_type="solid")
    STATUS_FILLS = {
        "OK": PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid"),
        "Riconferma sotto soglia": PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid"),
        "Preferenze non espresse": PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid"),
        "Da assegnare manualmente": PatternFill(start_color="FCE4EC", end_color="FCE4EC", fill_type="solid"),
    }
    SOGLIA_FILLS = {
        "Raggiunta": PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid"),
        "Non raggiunta": PatternFill(start_color="FCE4EC", end_color="FCE4EC", fill_type="solid"),
    }
    THIN = Border(
        left=Side(style="thin", color="B4C6E7"),
        right=Side(style="thin", color="B4C6E7"),
        top=Side(style="thin", color="B4C6E7"),
        bottom=Side(style="thin", color="B4C6E7"),
    )
    EUR_FMT = '#,##0.00\ "EUR"'

    def _fmt_sheet(ws, n_cols, fill_map=None, fill_col_idx=None, start_row=1):
        for ci in range(1, n_cols + 1):
            cell = ws.cell(row=start_row, column=ci)
            cell.font = HDR_FONT
            cell.fill = HDR_FILL
            cell.border = THIN
            cell.alignment = Alignment(horizontal="center", wrap_text=True, vertical="center")
        ws.row_dimensions[start_row].height = 28

        for ri in range(start_row + 1, ws.max_row + 1):
            is_zebra = (ri - start_row) % 2 == 0
            status_fill = None
            if fill_col_idx and fill_map:
                val = ws.cell(row=ri, column=fill_col_idx).value
                status_fill = fill_map.get(val)
            for ci in range(1, n_cols + 1):
                cell = ws.cell(row=ri, column=ci)
                cell.border = THIN
                if status_fill:
                    cell.fill = status_fill
                elif is_zebra:
                    cell.fill = ZEBRA_FILL

        for ci in range(1, n_cols + 1):
            max_len = 0
            for ri in range(start_row, min(ws.max_row + 1, 300)):
                val = ws.cell(row=ri, column=ci).value
                if val is not None:
                    max_len = max(max_len, len(str(val)))
            ws.column_dimensions[get_column_letter(ci)].width = min(max_len + 4, 45)
        ws.freeze_panes = ws.cell(row=start_row + 1, column=1).coordinate

    def _fmt_eur_cols(ws, col_names, start_row=1):
        for ci, name in enumerate(col_names, 1):
            if any(k in str(name) for k in ("EUR", "Imponibile", "Totale", "IVA")):
                for ri in range(start_row + 1, ws.max_row + 1):
                    ws.cell(row=ri, column=ci).number_format = EUR_FMT

    def _add_total_row(ws, col_names, data_start_row, sum_cols_keywords):
        sr = ws.max_row + 1
        ws.cell(row=sr, column=1).value = "TOTALE"
        ws.cell(row=sr, column=1).font = TOTAL_FONT
        for ci, name in enumerate(col_names, 1):
            if any(k in str(name) for k in sum_cols_keywords):
                total = sum(ws.cell(row=r, column=ci).value or 0 for r in range(data_start_row, sr))
                cell = ws.cell(row=sr, column=ci)
                cell.value = round(total, 2) if "EUR" in str(name) else total
                cell.font = TOTAL_FONT
                if "EUR" in str(name):
                    cell.number_format = EUR_FMT
            ws.cell(row=sr, column=ci).fill = TOTAL_FILL
            ws.cell(row=sr, column=ci).border = THIN
        return sr

    df_eco = calcola_colonne_economiche(
        df_assegnazioni, n_settimane, perc_decurtazione, costo_orario, aliquota_iva
    )

    organismi = sorted([o for o in df_eco["Organismo Assegnato dall'Algoritmo"].unique() if o])

    df_economico = calcola_riepilogo_economico(
        df_eco, n_settimane, perc_decurtazione, costo_orario, aliquota_iva
    )

    coop_cols = colonne_coop(perc_decurtazione, aliquota_iva)
    coop_cols_available = [c for c in coop_cols if c in df_eco.columns]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_eco.to_excel(writer, sheet_name="Assegnazioni", index=False)
        df_riepilogo.to_excel(writer, sheet_name="Riepilogo Gruppo", index=False)
        df_economico.to_excel(writer, sheet_name="Riepilogo Economico", index=False)
        df_criticita.to_excel(writer, sheet_name="Criticita", index=False)

        for org in organismi:
            mask = df_eco["Organismo Assegnato dall'Algoritmo"] == org
            df_o = df_eco.loc[mask, coop_cols_available].copy()

            safe_name = re.sub(r"[\\/*?\[\]:]", "", org)[:28].strip()
            if not safe_name:
                safe_name = "Organismo"
            seen_names = [s.title for s in writer.sheets.values()] if hasattr(writer, 'sheets') else []
            final_name = safe_name
            counter = 2
            while final_name in seen_names:
                final_name = f"{safe_name[:25]}_{counter}"
                counter += 1

            df_o.to_excel(writer, sheet_name=final_name, index=False, startrow=5)

    output.seek(0)
    wb = load_workbook(output)

    ws_ass = wb["Assegnazioni"]
    status_idx = list(df_eco.columns).index("Status") + 1 if "Status" in df_eco.columns else None
    _fmt_sheet(ws_ass, ws_ass.max_column, STATUS_FILLS, status_idx)
    _fmt_eur_cols(ws_ass, df_eco.columns)

    ws_grp = wb["Riepilogo Gruppo"]
    soglia_idx = list(df_riepilogo.columns).index("Soglia 45h") + 1 if "Soglia 45h" in df_riepilogo.columns else None
    _fmt_sheet(ws_grp, ws_grp.max_column, SOGLIA_FILLS, soglia_idx)

    ws_eco = wb["Riepilogo Economico"]
    _fmt_sheet(ws_eco, ws_eco.max_column)
    _fmt_eur_cols(ws_eco, df_economico.columns)
    _add_total_row(ws_eco, list(df_economico.columns), 2,
                   ("alunni", "Ore", "EUR", "IVA", "Imponibile", "Totale", "Decurtazione"))

    ws_crit = wb["Criticita"]
    status_idx_c = list(df_criticita.columns).index("Status") + 1 if "Status" in df_criticita.columns and len(df_criticita) > 0 else None
    _fmt_sheet(ws_crit, ws_crit.max_column, STATUS_FILLS, status_idx_c)

    today_str = datetime.date.today().strftime("%d/%m/%Y")
    for org in organismi:
        safe_name = re.sub(r"[\\/*?\[\]:]", "", org)[:28].strip() or "Organismo"
        ws = None
        for s in wb.sheetnames:
            if s.startswith(safe_name[:20]):
                ws = wb[s]
                break
        if ws is None:
            continue

        mask = df_eco["Organismo Assegnato dall'Algoritmo"] == org
        df_o = df_eco.loc[mask]
        ore_sett_tot = df_o["Ore Assegnate"].sum()
        n_al = len(df_o)
        imponibile_tot = df_o["Imponibile (EUR)"].sum()
        iva_tot = df_o[f"IVA {aliquota_iva:.0f}% (EUR)"].sum()
        totale_tot = df_o["Totale (EUR)"].sum()

        ore_lorde_tot = df_o["Ore annuali lorde"].sum()
        ore_nette_tot = df_o["Ore annuali nette"].sum()

        ws.cell(row=1, column=1).value = "ASSEGNAZIONE SERVIZIO OEPAC"
        ws.cell(row=1, column=1).font = TITLE_FONT
        ws.cell(row=2, column=1).value = org
        ws.cell(row=2, column=1).font = SUBTITLE_FONT
        ws.cell(row=3, column=1).value = (
            f"Data: {today_str}   |   Alunni assegnati: {n_al}   |   "
            f"Ore settimanali: {ore_sett_tot:.0f}   |   "
            f"Settimane: {n_settimane}   |   "
            f"Ore annuali nette (decurt. {perc_decurtazione:.0f}%): {ore_nette_tot:,.0f}"
        )
        ws.cell(row=3, column=1).font = PARAM_FONT
        ws.cell(row=4, column=1).value = (
            f"Costo orario: EUR {costo_orario:.2f}   |   "
            f"Imponibile: EUR {imponibile_tot:,.2f}   |   "
            f"IVA {aliquota_iva:.0f}%: EUR {iva_tot:,.2f}   |   "
            f"TOTALE: EUR {totale_tot:,.2f}"
        )
        ws.cell(row=4, column=1).font = SUBTITLE_FONT

        n_data_cols = len(coop_cols_available)
        _fmt_sheet(ws, n_data_cols, None, None, start_row=6)
        _fmt_eur_cols(ws, coop_cols_available, start_row=6)
        _add_total_row(ws, coop_cols_available, 7,
                       ("Ore", "EUR", "IVA", "Imponibile", "Totale", "Decurtazione"))

    final = io.BytesIO()
    wb.save(final)
    final.seek(0)
    return final.getvalue()


def _safe_filename(nome: str) -> str:
    """Nome file sicuro derivato dal nome organismo."""
    s = re.sub(r"[\\/*?\[\]:<>|\"']", "", nome).strip()
    s = re.sub(r"\s+", "_", s)
    return s[:60] or "Organismo"


def genera_zip_excel_cooperative(
    df_assegnazioni, df_riepilogo, df_criticita,
    n_settimane=35, perc_decurtazione=11.0, costo_orario=24.07, aliquota_iva=5.0,
) -> bytes:
    """Genera uno ZIP con un file .xlsx separato per ogni cooperativa
    (contenente SOLO i suoi alunni — privacy GDPR)."""
    import zipfile

    ORG = "Organismo Assegnato dall'Algoritmo"
    organismi = sorted([o for o in df_assegnazioni[ORG].unique() if o])

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for org in organismi:
            mask = df_assegnazioni[ORG] == org
            df_ass_o = df_assegnazioni.loc[mask].copy()
            gruppi_o = set(df_ass_o["Gruppo 45h"].unique())
            df_riep_o = df_riepilogo.loc[
                (df_riepilogo["Organismo"] == org)
                & (df_riepilogo["Gruppo 45h"].isin(gruppi_o))
            ].copy()
            df_crit_o = df_criticita.loc[
                df_criticita[ORG] == org
            ].copy() if ORG in df_criticita.columns else df_criticita.iloc[0:0].copy()

            xlsx_bytes = genera_excel(
                df_ass_o, df_riep_o, df_crit_o,
                n_settimane, perc_decurtazione, costo_orario, aliquota_iva,
            )
            zf.writestr(f"OEPAC_{_safe_filename(org)}.xlsx", xlsx_bytes)

    zip_buf.seek(0)
    return zip_buf.getvalue()


def genera_pdf_coop(
    df_eco_org, org, n_settimane=35, perc_decurtazione=11.0,
    costo_orario=24.07, aliquota_iva=5.0,
) -> bytes:
    """Genera una lettera di assegnazione PDF per una cooperativa."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    )

    BRAND = colors.HexColor("#1F4E79")
    BRAND_LIGHT = colors.HexColor("#D6E4F0")
    ZEBRA = colors.HexColor("#F2F7FB")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=14 * mm, bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=16,
                        textColor=BRAND, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12,
                        textColor=colors.HexColor("#2E75B6"), spaceAfter=8)
    normal = ParagraphStyle("n", parent=styles["Normal"], fontSize=9, leading=13)
    small = ParagraphStyle("s", parent=styles["Normal"], fontSize=8,
                           textColor=colors.HexColor("#666666"))

    iva_col = f"IVA {aliquota_iva:.0f}% (EUR)"
    ore_sett = df_eco_org["Ore Assegnate"].sum()
    ore_nette = df_eco_org["Ore annuali nette"].sum()
    imponibile = df_eco_org["Imponibile (EUR)"].sum()
    iva = df_eco_org[iva_col].sum()
    totale = df_eco_org["Totale (EUR)"].sum()
    n_al = len(df_eco_org)
    today_str = datetime.date.today().strftime("%d/%m/%Y")

    elems = []
    elems.append(Paragraph("ASSEGNAZIONE SERVIZIO OEPAC", h1))
    elems.append(Paragraph(org, h2))
    elems.append(Paragraph(
        f"Roma, {today_str} &nbsp;&nbsp;|&nbsp;&nbsp; "
        "Ai sensi dell'Art. 3, commi 5 e 6 delle Linee Guida approvate con "
        "DGC Roma Capitale n. 260/2024.", normal,
    ))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(
        f"Si comunica l'assegnazione del servizio OEPAC per <b>{n_al} alunni/e</b>, "
        f"per un totale di <b>{ore_sett:.0f} ore settimanali</b>. "
        f"Il computo economico, calcolato su <b>{n_settimane} settimane</b> con "
        f"decurtazione del <b>{perc_decurtazione:.0f}%</b> e costo orario di "
        f"<b>EUR {costo_orario:.2f}</b>, e riportato di seguito.", normal,
    ))
    elems.append(Spacer(1, 8))

    riepilogo_data = [
        ["Ore sett.", "Ore annue nette", "Imponibile", f"IVA {aliquota_iva:.0f}%", "TOTALE"],
        [
            f"{ore_sett:.0f}",
            f"{ore_nette:,.0f}",
            f"EUR {imponibile:,.2f}",
            f"EUR {iva:,.2f}",
            f"EUR {totale:,.2f}",
        ],
    ]
    rt = Table(riepilogo_data, hAlign="LEFT")
    rt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, 1), BRAND_LIGHT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B4C6E7")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elems.append(rt)
    elems.append(Spacer(1, 12))
    elems.append(Paragraph("Dettaglio alunni assegnati", h2))

    cols = [
        "Cognome", "Nome", "Grado Scolastico", "Plesso", "Classe", "Sezione",
        "Ore Assegnate", "Ore annuali nette", "Imponibile (EUR)", "Totale (EUR)",
    ]
    cols = [c for c in cols if c in df_eco_org.columns]
    header = [c.replace(" (EUR)", "").replace("Grado Scolastico", "Grado")
              .replace("Ore Assegnate", "Ore/sett").replace("Ore annuali nette", "Ore/anno")
              for c in cols]

    df_sorted = df_eco_org.sort_values(
        [c for c in ["Plesso", "Cognome", "Nome"] if c in df_eco_org.columns]
    )
    data = [header]
    for _, r in df_sorted.iterrows():
        row = []
        for c in cols:
            v = r[c]
            if "EUR" in c:
                row.append(f"{v:,.2f}")
            elif c in ("Ore annuali nette",):
                row.append(f"{v:,.0f}")
            else:
                row.append(str(v) if pd.notna(v) else "")
        data.append(row)

    tot_row = ["TOTALE"] + [""] * (len(cols) - 1)
    for i, c in enumerate(cols):
        if c == "Ore Assegnate":
            tot_row[i] = f"{ore_sett:.0f}"
        elif c == "Ore annuali nette":
            tot_row[i] = f"{ore_nette:,.0f}"
        elif c == "Imponibile (EUR)":
            tot_row[i] = f"{imponibile:,.2f}"
        elif c == "Totale (EUR)":
            tot_row[i] = f"{totale:,.2f}"
    data.append(tot_row)

    n_cols = len(cols)
    page_w = landscape(A4)[0] - 24 * mm
    name_w = page_w * 0.13
    other_w = (page_w - 2 * name_w) / (n_cols - 2) if n_cols > 2 else page_w / n_cols
    col_widths = []
    for c in cols:
        col_widths.append(name_w if c in ("Cognome", "Nome", "Plesso") else other_w)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B4C6E7")),
        ("ALIGN", (4, 1), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, -1), (-1, -1), BRAND_LIGHT),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]
    for ri in range(1, len(data) - 1):
        if ri % 2 == 0:
            style.append(("BACKGROUND", (0, ri), (-1, ri), ZEBRA))
    t.setStyle(TableStyle(style))
    elems.append(t)
    elems.append(Spacer(1, 10))
    elems.append(Paragraph(
        "Documento generato automaticamente dal sistema di assegnazione OEPAC. "
        "I dati riguardano alunni con disabilita e sono soggetti a riservatezza "
        "(Reg. UE 2016/679, art. 9).", small,
    ))

    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()


def genera_zip_pdf_cooperative(
    df_assegnazioni, n_settimane=35, perc_decurtazione=11.0,
    costo_orario=24.07, aliquota_iva=5.0,
) -> bytes:
    """ZIP con una lettera PDF di assegnazione per ogni cooperativa."""
    import zipfile

    ORG = "Organismo Assegnato dall'Algoritmo"
    df_eco = calcola_colonne_economiche(
        df_assegnazioni, n_settimane, perc_decurtazione, costo_orario, aliquota_iva
    )
    organismi = sorted([o for o in df_eco[ORG].unique() if o])

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for org in organismi:
            df_o = df_eco.loc[df_eco[ORG] == org].copy()
            pdf_bytes = genera_pdf_coop(
                df_o, org, n_settimane, perc_decurtazione, costo_orario, aliquota_iva
            )
            zf.writestr(f"Lettera_OEPAC_{_safe_filename(org)}.pdf", pdf_bytes)

    zip_buf.seek(0)
    return zip_buf.getvalue()


# ---------------------------------------------------------------------------
# Consistency checks
# ---------------------------------------------------------------------------

def verifiche_consistenza(df_result, df_input_work, col_map, stats) -> list[tuple[str, bool, str]]:
    checks = []

    checks.append((
        "Alunni processati",
        True,
        f"{stats['totale_alunni']} alunni con Stato=ATTIVA e senza rinuncia",
    ))

    all_have_status = df_result["Status"].notna().all() and (df_result["Status"] != "").all()
    checks.append((
        "Tutti gli alunni hanno status valorizzato",
        all_have_status,
        "OK" if all_have_status else "ERRORE: alcuni alunni senza status",
    ))

    riconferme_spostate = df_result.loc[
        (df_result["Tipo"].str.strip().str.upper() == "RICONFERMA")
        & (df_result["Organismo Assegnato dall'Algoritmo"] != "")
        & (df_result["Organismo Pre-esistente"] != "")
        & (df_result["Organismo Assegnato dall'Algoritmo"] != df_result["Organismo Pre-esistente"])
    ]
    ok_ric = len(riconferme_spostate) == 0
    checks.append((
        "Riconferme mantenute (nessuna spostata d'ufficio)",
        ok_ric,
        "OK" if ok_ric else f"ATTENZIONE: {len(riconferme_spostate)} riconferme con organismo diverso",
    ))

    ore_output = df_result["Ore Assegnate"].sum() if len(df_result) > 0 else 0
    ore_col = col_map.get("ore_assegnate")
    stato_col = col_map.get("stato")
    rinuncia_col = col_map.get("data_rinuncia")
    if ore_col and stato_col:
        mask_in = df_input_work[stato_col].str.strip().str.upper() == "ATTIVA"
        if rinuncia_col:
            mask_in &= df_input_work[rinuncia_col].isna() | (df_input_work[rinuncia_col].str.strip() == "")
        ore_input = pd.to_numeric(
            df_input_work.loc[mask_in, ore_col], errors="coerce"
        ).fillna(0).sum()
        ore_ok = abs(ore_output - ore_input) < 0.01
        checks.append((
            "Somma ore coerente",
            ore_ok,
            f"Input: {ore_input} — Output: {ore_output}"
            + ("" if ore_ok else " — DISALLINEAMENTO"),
        ))
    else:
        checks.append((
            "Somma ore coerente",
            True,
            f"Ore totali output: {ore_output}",
        ))

    return checks


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="Assegnazione OEPAC",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown("## Assegnazione automatica OEPAC")
    st.caption(
        "Art. 3, comma 5, Linee Guida DGC Roma Capitale n. 260/2024 — "
        "vincolo 45 ore settimanali per gruppo (IC / Ambito)"
    )

    with st.sidebar:
        st.header("Impostazioni")
        soglia = st.slider(
            "Soglia minima ore settimanali",
            min_value=0, max_value=100, value=45,
            help="L'Organismo deve raggiungere questo monte ore nel gruppo (IC o Ambito) per essere considerato viable.",
        )
        max_iter = st.number_input(
            "Iterazioni massime algoritmo",
            min_value=1, max_value=200, value=50,
        )
        st.divider()
        st.subheader("Parametri economici")
        n_settimane = st.number_input("Settimane annuali", min_value=1, max_value=52, value=35)
        perc_decurtazione = st.number_input("Decurtazione %", min_value=0.0, max_value=50.0, value=11.0, step=0.5)
        costo_orario = st.number_input("Costo orario (EUR)", min_value=0.0, value=24.07, step=0.01, format="%.2f")
        aliquota_iva = st.number_input("Aliquota IVA %", min_value=0.0, max_value=30.0, value=5.0, step=0.5)
        st.divider()
        with st.expander("Anagrafe plessi (opzionale)"):
            st.caption(
                "Per arricchire l'indirizzo del plesso. "
                "File .xlsx/.csv con colonne codice meccanografico e indirizzo. "
                "Scaricabile da dati.istruzione.it."
            )
            anagrafe_file = st.file_uploader(
                "File anagrafe",
                type=["xlsx", "csv"],
                key="anagrafe",
                label_visibility="collapsed",
            )

    uploaded = st.file_uploader(
        "Carica il file MESIS (.xlsx)",
        type=["xlsx"],
        key="mesis",
    )

    if uploaded is None:
        st.session_state.pop("risultati", None)
        st.session_state.pop("_last_file_id", None)
        st.info("Carica un file MESIS (.xlsx) per iniziare.")
        return

    file_id = f"{uploaded.name}_{uploaded.size}"
    if file_id != st.session_state.get("_last_file_id"):
        st.session_state.pop("risultati", None)
        st.session_state["_last_file_id"] = file_id

    file_bytes = uploaded.getvalue()
    df_raw, col_map, errors = carica_dati(file_bytes)

    if errors:
        for err in errors:
            st.error(err)
        if not col_map or df_raw.empty:
            return

    stato_col = col_map.get("stato")
    rinuncia_col = col_map.get("data_rinuncia")
    tipo_col = col_map.get("tipo")
    ore_col = col_map.get("ore_assegnate")
    mask_attiva = df_raw[stato_col].str.strip().str.upper() == "ATTIVA"
    if rinuncia_col:
        mask_attiva &= df_raw[rinuncia_col].isna() | (df_raw[rinuncia_col].str.strip() == "")
    n_attive = int(mask_attiva.sum())
    n_ric = 0
    n_nuove = 0
    if tipo_col:
        tipo_vals = df_raw.loc[mask_attiva, tipo_col].str.strip().str.upper()
        n_ric = int((tipo_vals == "RICONFERMA").sum())
        n_nuove = int((tipo_vals == "NUOVA ISCRIZIONE").sum())
    ore_tot = 0
    if ore_col:
        ore_tot = pd.to_numeric(df_raw.loc[mask_attiva, ore_col], errors="coerce").fillna(0).sum()

    st.markdown("#### Anteprima dati caricati")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Iscrizioni attive", f"{n_attive}")
    c2.metric("Riconferme", f"{n_ric}")
    c3.metric("Nuove iscrizioni", f"{n_nuove}")
    c4.metric("Ore totali", f"{ore_tot:,.0f}")

    organismi_set = set()
    org_col_name = col_map.get("organismo_assegnato")
    enti_col_name = col_map.get("enti_erogatori_scelti")
    if org_col_name:
        organismi_set.update(df_raw[org_col_name].dropna().str.strip().unique())
    if enti_col_name:
        for val in df_raw[enti_col_name].dropna():
            for pref in parse_preferenze(str(val)):
                organismi_set.add(pref.strip())
    organismi_set.discard("")
    organismi_list = sorted(organismi_set)

    filtro_org = "Tutti"
    if organismi_list:
        with st.sidebar:
            st.divider()
            filtro_org = st.selectbox(
                "Filtra per Organismo",
                ["Tutti"] + organismi_list,
                help="Filtra i risultati per mostrare solo gli alunni di un Organismo specifico.",
            )

    st.markdown("---")
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        run_clicked = st.button("Esegui assegnazione", type="primary", use_container_width=True)
    with col_info:
        st.caption(
            f"L'algoritmo assegnera le {n_nuove} nuove iscrizioni applicando "
            f"il vincolo di {soglia}h per gruppo (IC/Ambito)."
        )

    if run_clicked:
        with st.spinner("Elaborazione in corso..."):
            result = esegui_assegnazione(df_raw, col_map, soglia, max_iter)
            df_assegnazioni, df_riepilogo, df_criticita, log_lines, stats, nome_registro = result
            if anagrafe_file:
                df_assegnazioni = arricchisci_indirizzi(
                    df_assegnazioni, anagrafe_file.getvalue(), filename=anagrafe_file.name,
                )
        st.session_state["risultati"] = {
            "df_assegnazioni": df_assegnazioni,
            "df_riepilogo": df_riepilogo,
            "df_criticita": df_criticita,
            "log": log_lines,
            "stats": stats,
            "df_raw": df_raw,
            "col_map": col_map,
        }

    if "risultati" not in st.session_state:
        return

    res = st.session_state["risultati"]
    df_assegnazioni = res["df_assegnazioni"]
    df_riepilogo = res["df_riepilogo"]
    df_criticita = res["df_criticita"]
    log_lines = res["log"]
    stats = res["stats"]

    st.markdown("---")
    st.markdown("### Risultati")

    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        st.metric("Spostamenti effettuati", stats["spostamenti"])
    with rc2:
        st.metric("Iterazioni algoritmo", stats["iterazioni"])
    with rc3:
        n_crit = stats["criticita"]
        st.metric("Casi da verificare", n_crit, delta=None if n_crit == 0 else f"{n_crit} criticita", delta_color="off" if n_crit == 0 else "inverse")

    checks = verifiche_consistenza(
        df_assegnazioni, res["df_raw"], res["col_map"], stats
    )
    with st.expander("Verifiche di consistenza", expanded=False):
        for label, ok, detail in checks:
            icon = "pass" if ok else "fail"
            st.markdown(f":{'green' if ok else 'red'}[{'OK' if ok else 'ATTN'}] **{label}** — {detail}")

    df_display = df_assegnazioni.copy()
    if filtro_org != "Tutti":
        mask = (
            df_display["Organismo Assegnato dall'Algoritmo"].apply(
                lambda x: nomi_uguali(x, filtro_org) if isinstance(x, str) else False
            )
            | df_display["Organismo Pre-esistente"].apply(
                lambda x: nomi_uguali(x, filtro_org) if isinstance(x, str) else False
            )
        )
        df_display = df_display.loc[mask]
        df_riep_display = df_riepilogo.loc[
            df_riepilogo["Organismo"].apply(
                lambda x: nomi_uguali(x, filtro_org) if isinstance(x, str) else False
            )
        ]
    else:
        df_riep_display = df_riepilogo

    tab_ass, tab_riep, tab_crit, tab_graf, tab_log = st.tabs([
        f"Assegnazioni ({len(df_display)})",
        f"Riepilogo Gruppo ({len(df_riep_display)})",
        f"Criticita ({len(df_criticita)})",
        "Grafici",
        "Log",
    ])

    with tab_ass:
        edit_mode = st.toggle(
            "Modifica manuale assegnazioni",
            help="Permette di cambiare l'Organismo assegnato a un alunno e ricalcolare i riepiloghi.",
        )
        if edit_mode:
            st.caption(
                "Modifica la colonna **Organismo Assegnato dall'Algoritmo**, "
                "poi clicca **Applica modifiche** per ricalcolare riepiloghi e importi. "
                "Le modifiche manuali sono evidenziate con Preferenza = 'Manuale'."
            )
            org_options = sorted([o for o in df_assegnazioni["Organismo Assegnato dall'Algoritmo"].unique() if o])
            edited = st.data_editor(
                df_display,
                use_container_width=True,
                hide_index=True,
                height=500,
                key="editor_ass",
                column_config={
                    "Organismo Assegnato dall'Algoritmo": st.column_config.SelectboxColumn(
                        "Organismo Assegnato dall'Algoritmo",
                        options=org_options,
                        required=False,
                    ),
                },
                disabled=[c for c in df_display.columns if c != "Organismo Assegnato dall'Algoritmo"],
            )
            if st.button("Applica modifiche e ricalcola", type="primary"):
                df_full = df_assegnazioni.set_index("Codice Iscrizione")
                ed = edited.set_index("Codice Iscrizione")
                n_mod = 0
                for cod, row in ed.iterrows():
                    nuovo = row["Organismo Assegnato dall'Algoritmo"]
                    if cod in df_full.index:
                        vecchio = df_full.at[cod, "Organismo Assegnato dall'Algoritmo"]
                        if str(nuovo) != str(vecchio):
                            df_full.at[cod, "Organismo Assegnato dall'Algoritmo"] = nuovo
                            df_full.at[cod, "Preferenza Soddisfatta"] = "Manuale"
                            df_full.at[cod, "Status"] = "OK" if nuovo else "Da assegnare manualmente"
                            df_full.at[cod, "Note"] = "Assegnazione modificata manualmente"
                            n_mod += 1
                df_new = df_full.reset_index()
                new_riep = costruisci_riepilogo_gruppo(df_new, soglia)
                new_crit = costruisci_criticita(df_new)
                st.session_state["risultati"]["df_assegnazioni"] = df_new
                st.session_state["risultati"]["df_riepilogo"] = new_riep
                st.session_state["risultati"]["df_criticita"] = new_crit
                st.session_state["risultati"]["stats"]["criticita"] = int((df_new["Status"] != "OK").sum())
                st.success(f"{n_mod} assegnazioni modificate. Riepiloghi ricalcolati.")
                st.rerun()
        else:
            st.dataframe(df_display, use_container_width=True, hide_index=True, height=500)

    with tab_riep:
        if not df_riep_display.empty:
            st.dataframe(df_riep_display, use_container_width=True, hide_index=True, height=400)
        else:
            st.info("Nessun dato nel riepilogo per il filtro selezionato.")

    with tab_crit:
        if not df_criticita.empty:
            st.dataframe(df_criticita, use_container_width=True, hide_index=True, height=400)
        else:
            st.success("Nessuna criticita rilevata.")

    with tab_graf:
        _mostra_grafici(df_assegnazioni, df_riepilogo,
                        n_settimane, perc_decurtazione, costo_orario, aliquota_iva)

    with tab_log:
        for entry in log_lines:
            st.text(entry)

    st.markdown("---")
    st.markdown("### Download")
    st.caption(
        "Il file completo contiene tutti i dati. I file separati e le lettere PDF "
        "contengono solo i dati della singola cooperativa (idoneo all'invio diretto, GDPR)."
    )
    d1, d2, d3 = st.columns(3)
    with d1:
        excel_bytes = genera_excel(
            df_assegnazioni, df_riepilogo, df_criticita,
            n_settimane, perc_decurtazione, costo_orario, aliquota_iva,
        )
        st.download_button(
            "Report completo (.xlsx)",
            data=excel_bytes,
            file_name="assegnazioni_output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )
        st.caption("Tutte le cooperative in un unico file.")
    with d2:
        zip_xlsx = genera_zip_excel_cooperative(
            df_assegnazioni, df_riepilogo, df_criticita,
            n_settimane, perc_decurtazione, costo_orario, aliquota_iva,
        )
        st.download_button(
            "File separati per coop (.zip)",
            data=zip_xlsx,
            file_name="assegnazioni_per_cooperativa.zip",
            mime="application/zip",
            use_container_width=True,
        )
        st.caption("Un .xlsx per ogni cooperativa.")
    with d3:
        zip_pdf = genera_zip_pdf_cooperative(
            df_assegnazioni, n_settimane, perc_decurtazione, costo_orario, aliquota_iva,
        )
        st.download_button(
            "Lettere di assegnazione (.zip PDF)",
            data=zip_pdf,
            file_name="lettere_assegnazione.zip",
            mime="application/zip",
            use_container_width=True,
        )
        st.caption("Una lettera PDF per ogni cooperativa.")


def _mostra_grafici(df_ass, df_riep, n_settimane, perc_decurtazione, costo_orario, aliquota_iva):
    import altair as alt

    ORG = "Organismo Assegnato dall'Algoritmo"
    df_assegnati = df_ass[df_ass[ORG].astype(str).str.len() > 0]
    if df_assegnati.empty:
        st.info("Nessun dato da visualizzare.")
        return

    df_eco = calcola_colonne_economiche(
        df_assegnati, n_settimane, perc_decurtazione, costo_orario, aliquota_iva
    )

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Ore settimanali per cooperativa**")
        per_org = df_eco.groupby(ORG)["Ore Assegnate"].sum().reset_index()
        per_org.columns = ["Cooperativa", "Ore"]
        chart = alt.Chart(per_org).mark_bar(color="#2E75B6").encode(
            x=alt.X("Ore:Q", title="Ore settimanali"),
            y=alt.Y("Cooperativa:N", sort="-x", title=None),
            tooltip=["Cooperativa", "Ore"],
        ).properties(height=max(150, 40 * len(per_org)))
        st.altair_chart(chart, use_container_width=True)

    with g2:
        st.markdown("**Alunni per cooperativa**")
        per_org_n = df_eco.groupby(ORG).size().reset_index(name="Alunni")
        per_org_n.columns = ["Cooperativa", "Alunni"]
        chart2 = alt.Chart(per_org_n).mark_bar(color="#1F4E79").encode(
            x=alt.X("Alunni:Q", title="N. alunni"),
            y=alt.Y("Cooperativa:N", sort="-x", title=None),
            tooltip=["Cooperativa", "Alunni"],
        ).properties(height=max(150, 40 * len(per_org_n)))
        st.altair_chart(chart2, use_container_width=True)

    g3, g4 = st.columns(2)
    with g3:
        st.markdown("**Importo totale annuo per cooperativa (EUR)**")
        per_org_eur = df_eco.groupby(ORG)["Totale (EUR)"].sum().reset_index()
        per_org_eur.columns = ["Cooperativa", "Totale"]
        chart3 = alt.Chart(per_org_eur).mark_bar(color="#2E9B5B").encode(
            x=alt.X("Totale:Q", title="EUR", axis=alt.Axis(format=",.0f")),
            y=alt.Y("Cooperativa:N", sort="-x", title=None),
            tooltip=["Cooperativa", alt.Tooltip("Totale:Q", format=",.2f")],
        ).properties(height=max(150, 40 * len(per_org_eur)))
        st.altair_chart(chart3, use_container_width=True)

    with g4:
        st.markdown("**Preferenze soddisfatte (nuove iscrizioni)**")
        pref = df_eco[df_eco["Preferenza Soddisfatta"].isin(
            ["1ª", "2ª", "3ª", "4ª", "5ª", "Manuale", "Non assegnato"]
        )]["Preferenza Soddisfatta"].value_counts().reset_index()
        pref.columns = ["Preferenza", "Alunni"]
        if not pref.empty:
            chart4 = alt.Chart(pref).mark_arc(innerRadius=50).encode(
                theta="Alunni:Q",
                color=alt.Color("Preferenza:N", scale=alt.Scale(scheme="blues")),
                tooltip=["Preferenza", "Alunni"],
            ).properties(height=250)
            st.altair_chart(chart4, use_container_width=True)
        else:
            st.caption("Nessuna nuova iscrizione da mostrare.")

    st.markdown("**Distribuzione per grado scolastico**")
    grado = df_eco.groupby("Grado Scolastico").agg(
        Alunni=("Codice Iscrizione", "count"),
        Ore=("Ore Assegnate", "sum"),
    ).reset_index()
    st.dataframe(grado, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
