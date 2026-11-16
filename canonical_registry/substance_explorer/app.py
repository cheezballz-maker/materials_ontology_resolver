"""Launch with python -m streamlit run canonical_registry/substance_explorer/app.py."""

from html import escape
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import streamlit as st

# Streamlit executes this file as a script, independent of the shell import path.
workspace = str(Path(__file__).resolve().parents[2])
if workspace not in sys.path:
    sys.path.insert(0, workspace)
from canonical_registry.substance_explorer.registry_search import (  # noqa: E402
    MAX_QUERY, PAGE_SIZE, Query, Registry, interpret,
)
from canonical_registry.substance_explorer.registry_access import (  # noqa: E402
    ConceptSnapshot, RegistryAccess, concept_datasets, snapshot_digest, substance_datasets,
)
from canonical_registry.substance_explorer.resolution_bridge import REASONS, resolve  # noqa: E402
from canonical_registry.substance_explorer.structure_display import depiction, molecular_formula, stereo_summary  # noqa: E402


@st.cache_data(max_entries=48, show_spinner=False)
def cached_depiction(smiles):
    return depiction(smiles)


@st.cache_data(max_entries=32, show_spinner=False)
def cached_digest(path, snapshot_token):
    return snapshot_digest(path)


def fingerprint(registry):
    return cached_digest(registry.path, registry.snapshot_token())


def show_table(headers, rows):
    head = "".join(f'<th scope="col">{escape(col)}</th>' for col in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(cell) if cell is not None else '—')}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    st.html(f"""
        <style>
        .explorer-table {{overflow-x:auto}}
        .explorer-table table {{width:100%; table-layout:fixed; border-collapse:collapse; font-size:.88rem}}
        .explorer-table th,.explorer-table td {{
            border-bottom:1px solid rgba(128,128,128,.28); padding:.5rem .55rem;
            text-align:left; vertical-align:top; overflow-wrap:anywhere;
        }}
        .explorer-table th {{background:rgba(128,128,128,.10)}}
        .explorer-table th:first-child {{width:25%}}
        </style>
        <div class="explorer-table"><table>
          <thead><tr>{head}</tr></thead><tbody>{body}</tbody>
        </table></div>
    """)


def fields_table(rows):
    body = "".join(
        f"<tr><th scope='row'>{escape(str(label))}</th><td>{escape(str(value))}</td></tr>"
        for label, value in rows if value
    )
    if body:
        st.html(f'<table class="registry-fields"><tbody>{body}</tbody></table>')


def show_structure(smiles, rows):
    drawing = cached_depiction(smiles) if smiles else None
    if drawing:
        diagram, details = st.columns([1, 3], gap="small", vertical_alignment="center")
        diagram.image(drawing, width=180)
        with details:
            fields_table(rows)
    else:
        fields_table(rows)


def show_detail(registry, sid):
    record = registry.detail(sid)
    if not record:
        st.warning("This Substance ID was not found.")
        return
    with st.container(border=True):
        st.subheader(record["preferred_name"], anchor=False)
        st.caption(f"{sid} · {display_label(record['identity_status'])}")
        smiles = next((row["structure_value"] for row in record["structures"]
                       if row["structure_type"] == "SMILES"), None)
        rows = [("Molecular formula", molecular_formula(smiles))]
        rows.extend((row["structure_type"], row["structure_value"]) for row in record["structures"])
        rows.extend((row["identifier_type"], row["identifier_value"]) for row in record["identifiers"])
        show_structure(smiles, rows)
        fields_table([("Aliases", " · ".join(record["aliases"])),
                      ("CUMA reconciliation", f"{len(record['cuma_indices']):,} exact records"
                       if record.get("cuma_indices") else None)])
        if record["sources"]:
            st.markdown("**Exact source links**")
            show_table(("Source", "Record ID", "Names"), (
                (row["source_system"], row["source_record_id"],
                 " · ".join(dict.fromkeys(row["source_labels"].values())))
                for row in record["sources"]
            ))


def display_label(value):
    return str(value).replace("_", " ").capitalize()


def show_resolution(result, search_hits):
    with st.container(border=True):
        st.markdown("**Structure comparison**")
        fields_table([
            ("Result", display_label(result["status"])),
            ("Match", result.get("matched_substance_id")),
            ("Equivalent IDs", ", ".join(result.get("equivalent_ids", []))),
            ("Search", ("Complete" if result["search_complete"] else "Incomplete")
             if "search_complete" in result else f"{search_hits} search candidates on this page"),
            ("Structural validation", display_label(result["structural_validity"])
             if "structural_validity" in result else None),
        ])
        if "search_complete" in result:
            st.caption("Comparison of the represented graph. Source admission was not assessed.")
        for code in result["reason_codes"]:
            key = code.split(":", 1)[0]
            st.caption(REASONS.get(key, display_label(key)))
        if result.get("detail"):
            st.text(result["detail"])
        rows = {row["substance_id"]: row for row in result.get("comparisons", [])}
        relevant = [rows[sid] for sid in result.get("relevant_ids", [])]
        if relevant:
            show_table(("Candidate ID", "Name", "Comparison"), (
                (row["substance_id"], row["preferred_name"], display_label(row["chemical_status"]))
                for row in relevant
            ))

SUBSTANCE_SEARCH_FIELDS = {
    "Auto": "", "Name or alias": "name:", "Substance ID": "",
    "Formula": "formula:", "InChIKey": "inchikey:", "InChI": "inchi:",
    "PubChem CID": "pubchemcid:", "ChEBI ID": "chebi:", "CAS number": "cas:",
    "EC number": "ec:", "Warehouse record ID": "patsnap:", "SMILES": "smiles:",
}
CONCEPT_SEARCH_FIELDS = {"Name or ID": "", "Formula": "formula:", "Source record ID": "source:"}
SOURCE_FILTERS = {"All substances": None, "With exact source association": True,
                  "Without exact source association": False}
CONCEPT_FILTERS = {"All types": None, "Molecular concepts": "molecular", "Chemical families": "family"}


def search_form(section, fields, filter_label, filters, placeholder):
    with st.form(f"{section}-search-form"):
        text, field, filter_column, submit = st.columns([5, 2, 2, 1], vertical_alignment="bottom")
        value = text.text_input(f"Search {section}", key=f"{section}-search", max_chars=MAX_QUERY,
                                placeholder=placeholder)
        search_field = field.selectbox("Search by", tuple(fields), key=f"{section}-field")
        data_filter = filter_column.selectbox(filter_label, tuple(filters), key=f"{section}-filter")
        submitted = submit.form_submit_button("Search", type="primary")
    value = value.strip()
    prefix = fields[search_field]
    if prefix and value and not value.casefold().startswith(prefix):
        value = prefix + value
    return submitted, value, search_field, filters[data_filter]


def select_record(section, sid):
    st.session_state[f"{section}-selected"] = sid
    if section == "substances":
        st.session_state.pop("linked-substance", None)


def record_list(section, labels):
    if not labels:
        st.caption("No matching records.")
        return None
    selection_key = f"{section}-selected"
    widget_key = f"{section}-records"
    selected = st.session_state.get(selection_key)
    if selected not in labels:
        selected = next(iter(labels))
    if st.session_state.get(widget_key) != selected:
        st.session_state[widget_key] = selected
    with st.container(height=min(360, 56 + 42 * len(labels)), border=True, key=f"{section}-list"):
        return st.radio("Records", list(labels), index=None, key=widget_key,
                        format_func=labels.__getitem__, label_visibility="collapsed",
                        on_change=select_record_from_list, args=(section, widget_key))


def select_record_from_list(section, widget_key):
    select_record(section, st.session_state[widget_key])


def id_list(section, rows, id_field, *, page=0, more=False):
    st.caption("Click a record or use ↑ and ↓ to browse.")
    selected = record_list(section, {row[id_field]: row[id_field] for row in rows})
    if page or more:
        previous, following = st.columns(2)
        if previous.button("Previous", disabled=page == 0, width="stretch"):
            st.session_state["substances-page"] = page - 1
            select_record(section, None)
            st.rerun()
        if following.button("Next", disabled=not more, width="stretch"):
            st.session_state["substances-page"] = page + 1
            select_record(section, None)
            st.rerun()
        st.caption(f"Page {page + 1} · Up to {PAGE_SIZE} records")
    return selected

def show_substances(registry, substance_options):
    submitted, value, field, source_linked = search_form(
        "substances", SUBSTANCE_SEARCH_FIELDS, "Source links", SOURCE_FILTERS,
        "Name, Substance ID, or identifier",
    )
    if submitted:
        select_record("substances", None)
        for key in ("result", "audit", "substances-query"):
            st.session_state.pop(key, None)
        st.session_state["substances-page"] = 0
        st.session_state["substances-source-linked"] = source_linked
        try:
            query = interpret(value) if value else Query("", "browse", "")
            if field == "Substance ID" and value and query.kind != "canonical ID":
                raise ValueError("Enter a Substance ID such as SUB_00000006.")
            st.session_state["substances-query"] = query
        except ValueError as exc:
            st.warning(str(exc))
            return
    query = st.session_state.get("substances-query") or Query("", "browse", "")
    page = st.session_state.get("substances-page", 0)
    try:
        rows, more = registry.search(query, page=page,
                                     source_linked=st.session_state.get("substances-source-linked"))
    except ValueError as exc:
        st.warning(str(exc))
        return
    left, right = st.columns([1, 4], gap="small")
    with left:
        selected = id_list("substances", rows, "substance_id", page=page, more=more)
    with right:
        result = st.session_state.get("result")
        if result and "snapshot_stamp" in result and result["snapshot_stamp"] != list(registry.snapshot_token()):
            st.session_state.pop("result", None)
            result = None
            st.warning("The registry changed. Run the comparison again.")
        detail = st.container()
        if query.kind not in {"browse", "formula"}:
            if query.kind == "patsnap" and (record := registry.source_record(query.value)):
                fields_table([("Warehouse record", record["original_substance_id"]),
                              ("Source names", " · ".join(dict.fromkeys(record["source_labels"].values())))])
            if st.button("Attempt Resolution"):
                with st.spinner("Comparing chemical evidence…"):
                    result = st.session_state.result = resolve(registry.path, query)
            if result:
                show_resolution(result, len(rows))
        with detail:
            if linked := st.session_state.get("linked-substance"):
                dataset_key, sid = linked
                dataset = substance_options[dataset_key]
                show_detail(Registry(dataset.path, live=dataset.live), sid)
            elif sid := selected or (result or {}).get("matched_substance_id"):
                show_detail(registry, sid)


def switch_to_substance(dataset_key, sid):
    st.session_state.registry_section = "Substances"
    select_record("substances", None)
    st.session_state["linked-substance"] = (dataset_key, sid)


def open_related_concept(sid):
    st.session_state["concepts-search"] = ""
    st.session_state["concepts-field"] = "Name or ID"
    st.session_state["concepts-filter"] = "All types"
    st.session_state.pop("concepts-criteria", None)
    select_record("concepts", sid)


def show_concepts(registry, substance_options):
    submitted, value, _, definition_kind = search_form(
        "concepts", CONCEPT_SEARCH_FIELDS, "Concept type", CONCEPT_FILTERS, "Name or ChemicalConcept ID",
    )
    if submitted:
        st.session_state["concepts-criteria"] = (value, definition_kind)
        select_record("concepts", None)
    text, kind = st.session_state.get("concepts-criteria", ("", None))
    rows = registry.search(text, definition_kind=kind)
    left, right = st.columns([1, 4], gap="small")
    with left:
        selected = id_list("concepts", rows, "concept_id")
    with right:
        if selected:
            show_concept_detail(registry, selected, substance_options)
        else:
            st.info("Select a ChemicalConcept ID to view its details.")


def show_concept_detail(registry, sid, substance_options):
    record = registry.detail(sid)
    if not record:
        st.warning("This ChemicalConcept ID was not found.")
        return
    definition = record["definition"]
    with st.container(border=True):
        st.subheader(record["preferred_label"], anchor=False)
        st.caption(f"{sid} · {display_label(definition.get('kind', 'concept'))}")
        labels = [row["label"] for row in record["labels"] if row["label"] != record["preferred_label"]]
        fields_table([("Definition", definition.get("definition")), ("Other names", " · ".join(labels))])
        if smiles := definition.get("smiles"):
            show_structure(smiles, [
                ("Molecular formula", molecular_formula(smiles)),
                ("SMILES", smiles),
                ("Stereochemistry", display_label(definition["stereo_state"]) if definition.get("stereo_state") else None),
            ])
            if stereo := stereo_summary(smiles):
                show_table(("Stereogenic feature", "Configuration", "Descriptor"), stereo)
        for relation in ("broader", "narrower"):
            if record[relation]:
                st.markdown(f"**{relation.title()} concepts**")
            for related in record[relation]:
                target = related["concept_id"]
                if detail := registry.detail(target):
                    st.button(f"{target} · {detail['preferred_label']}", key=f"{relation}-{sid}-{target}",
                              on_click=open_related_concept, args=(target,))
        if record["members"]:
            st.markdown("**Validated Substance members**")
            fingerprints = {}
            for key, option in substance_options.items():
                try:
                    fingerprints[key] = fingerprint(Registry(option.path))
                except (OSError, sqlite3.Error, ValueError):
                    continue
            for member in record["members"]:
                target = RegistryAccess.member_target(member, substance_options, fingerprints)
                member_id = member["substance_id"]
                if target:
                    st.button(member_id, key=f"member-{sid}-{member_id}",
                              on_click=switch_to_substance, args=(target, member_id))
                else:
                    st.caption(f"{member_id} · Details unavailable")
        if record["mappings"]:
            st.markdown("**Source mappings**")
            show_table(("Source", "Record type", "Record ID"), (
                (row["source_system"], row["record_type"], row["record_id"]) for row in record["mappings"]
            ))

def show_enrichment():
    from canonical_registry.enrichment.development import open_development
    from canonical_registry.enrichment.workflow import ChemicalInput, Enrichment, read_inputs

    try:
        permit, concepts = open_development()
    except FileNotFoundError:
        st.info("Initialize the development databases from the workspace root.")
        st.code("python -m canonical_registry.enrichment init")
        return
    st.subheader("Resolve Chemicals", anchor=False)
    mode = st.radio("Input mode", ("Names or CSV", "Single with evidence", "Look up ID"),
                    horizontal=True, label_visibility="collapsed", key="enrichment-mode")
    if mode == "Look up ID":
        sid = st.text_input("Development Substance or ChemicalConcept ID", key="enrichment-stored-id",
                            placeholder="SUB_… or CC_…").strip().upper()
        show_development_record(permit, concepts, sid)
        return

    fields, csv_file, evidence = {}, None, None
    with st.form("chemical-preview"):
        if mode == "Names or CSV":
            names_col, file_col = st.columns([2, 1], gap="medium")
            names = names_col.text_area("Chemical names", placeholder="One name per line", height=100)
            file_col.caption("Use names or upload a CSV with a name column. Up to 30 inputs.")
            csv_file = file_col.file_uploader("CSV file", type="csv", label_visibility="collapsed")
        else:
            names = st.text_input("Chemical name (optional with a structure)", placeholder="e.g. water or butan-2-ol")
            structures, identifiers, source = st.columns(3, gap="medium")
            with structures:
                st.markdown("**Structure**")
                fields["smiles"] = st.text_input("SMILES")
                fields["inchi"] = st.text_input("InChI")
                fields["inchikey"] = st.text_input("InChIKey (optional check)")
            with identifiers:
                st.markdown("**Identifiers and names**")
                fields["cas"] = st.text_input("CAS number")
                fields["ec"] = st.text_input("EC number")
                fields["inci_name"] = st.text_input("INCI name")
            with source:
                st.markdown("**Source record**")
                fields["source_system"] = st.text_input("Source namespace")
                fields["source_record_id"] = st.text_input("Source record ID")
            evidence = st.file_uploader("Optional saved provider evidence", type="json",
                                        help="Optional PubChem or ChEBI evidence packet with its retained payload and SHA-256.")
        submitted = st.form_submit_button("Preview", type="primary")
    if submitted:
        st.session_state.pop("enrichment-preview", None)
        try:
            if (csv_file and names.strip()) or any(f and f.size > 128_000 for f in (csv_file, evidence)):
                raise ValueError("Use either names or CSV. Uploads are limited to 128 KB.")
            inputs = read_inputs(csv_file.getvalue().decode("utf-8-sig") if csv_file else names,
                                 csv_input=bool(csv_file))
            packet = json.loads(evidence.getvalue()) if evidence else None
            if packet is not None and not isinstance(packet, dict):
                raise ValueError("Saved evidence must be a JSON object.")
            if any(fields.values()) or packet:
                if len(inputs) > 1 or csv_file:
                    raise ValueError("Use one chemical for these fields. CSV accepts per-row fields.")
                inputs = [ChemicalInput(inputs[0].name if inputs else "", **fields)]
            with st.spinner("Interpreting and comparing chemical identities…"), Enrichment() as service:
                previews = ([service.resolve(inputs[0], saved_evidence=packet)] if packet else service.batch(inputs))
            st.session_state["enrichment-preview"] = (inputs, packet, previews)
            st.session_state.pop("enrichment-receipts", None)
            select_record("preview", None)
            st.session_state["enrichment-preview-number"] = st.session_state.get("enrichment-preview-number", 0) + 1
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            st.error(str(exc))
    state = st.session_state.get("enrichment-preview")
    if not state:
        return
    inputs, packet, previews = state
    left, right = st.columns([1, 2], gap="small")
    with left:
        st.markdown("**Preview results**")
        selected = record_list("preview", {
            i: f"{i + 1}. {item.name} · {display_label(previews[i]['outcome'])}"
            for i, item in enumerate(inputs)
        })
        eligible = [i for i, result in enumerate(previews) if result["commit_eligible"]]
        if eligible:
            st.caption("Choose records to save to the development registry.")
            preview_number = st.session_state["enrichment-preview-number"]
            with st.form("enrichment-commit"):
                with st.container(height=min(245, 54 + 42 * len(eligible)), border=False):
                    chosen = [i for i in eligible if st.checkbox(
                        f"{i + 1}. {inputs[i].name}", key=f"commit-{preview_number}-{i}")]
                commit = st.form_submit_button("Commit selected to development")
            if commit and chosen:
                try:
                    with st.spinner("Revalidating and committing selected rows…"), Enrichment() as service:
                        receipts = {i: service.commit(inputs[i], previews[i], saved_evidence=packet) for i in chosen}
                    st.session_state.setdefault("enrichment-receipts", {}).update(receipts)
                except (OSError, subprocess.SubprocessError) as exc:
                    st.error(str(exc))
            elif commit:
                st.caption("Select at least one eligible record.")
    with right:
        row = previews[selected]
        receipt = st.session_state.get("enrichment-receipts", {}).get(selected, {})
        sid = receipt.get("committed_id") or row["substance_id"] or row["concept_id"]
        with st.container(border=True):
            st.subheader(inputs[selected].name, anchor=False)
            st.caption(display_label(row["outcome"]))
            fields_table([
                ("Validation", display_label(row["validation"])),
                ("SMILES", (row["interpretation"] or {}).get("smiles")),
                ("Existing ID", row["substance_id"] or row["concept_id"]),
                ("Action", ("Eligible to reuse" if row["substance_id"] or row["concept_id"] else "Eligible to create")
                 if row["commit_eligible"] else "Preview only"),
                ("Commit result", display_label(receipt["outcome"]) if receipt else None),
                ("Committed ID", receipt.get("committed_id")),
            ])
            for reason in dict.fromkeys([*row["diagnostics"], *receipt.get("diagnostics", [])]):
                st.caption(REASONS.get(reason, display_label(reason) if reason.isupper() else reason))
        show_development_record(permit, concepts, sid)


def show_development_record(permit, concepts, sid):
    if sid and sid.startswith("SUB_"):
        show_detail(Registry(permit.path, live=True), sid)
    elif sid and sid.startswith("CC_"):
        show_concept_detail(ConceptSnapshot(concepts.path, live=True), sid, substance_datasets())
    elif sid:
        st.caption("Enter a Substance ID starting with SUB_ or a ChemicalConcept ID starting with CC_.")

def main():
    st.set_page_config(page_title="Registry Explorer", page_icon="⚗️", layout="wide")
    st.html("""
        <style>
        [data-testid="stMainBlockContainer"] {max-width: none; padding: 4.25rem 1.25rem 2rem;}
        @media (min-width: 900px) {
            [data-testid="stSidebar"][aria-expanded="true"] {width: 13rem !important;}
        }
        [data-testid="stMain"] h1 {font-size: 1.65rem; padding: 0;}
        [data-testid="stMain"] h3 {font-size: 1.2rem; padding: 0; overflow-wrap: anywhere;}
        [data-testid="stMain"] [data-testid="stVerticalBlock"] {gap: .65rem;}
        [data-testid="stMain"] [data-testid="stWidgetLabel"] p,
        [data-testid="stMain"] [data-testid="stMarkdownContainer"] p {font-size: .9rem;}
        .registry-fields {border-collapse: collapse; width: 100%; font-size: .88rem;}
        .registry-fields th, .registry-fields td {
            padding: .32rem .45rem; text-align: left; vertical-align: top;
            border-bottom: 1px solid rgba(128,128,128,.24); overflow-wrap: anywhere;
        }
        .registry-fields th {width: 29%; font-weight: 600;}
        :is(.st-key-substances-list, .st-key-concepts-list, .st-key-preview-list) [role="radiogroup"] p {
            display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2;
            overflow: hidden; overflow-wrap: anywhere; line-height: 1.25;
        }
        [data-testid="stRadio"] label:focus-within {outline: 2px solid currentColor; outline-offset: 2px;}
        @media (max-width: 720px) {
            [data-testid="stMainBlockContainer"] {padding: 4.25rem 1rem 2rem;}
        }
        </style>
    """)
    st.title("Registry Explorer")
    section = st.sidebar.radio("Registry", ("Substances", "Chemical Concepts", "Resolve Chemicals"),
                               key="registry_section")
    substances = substance_datasets()
    try:
        if section == "Resolve Chemicals":
            show_enrichment()
        elif section == "Substances":
            access = RegistryAccess(next(iter(substances.values())))
            show_substances(access.substances, substances)
        else:
            concepts = concept_datasets()
            concept_dataset = concepts.get("development") or concepts.get("demo")
            if concept_dataset is None:
                st.warning("The default ChemicalConcept registry is unavailable.")
                return
            access = RegistryAccess(concepts=concept_dataset)
            show_concepts(access.concepts, substances)
    except (OSError, sqlite3.Error, ValueError) as exc:
        st.error("The registry could not complete this read.")
        st.text(str(exc))


if __name__ == "__main__":
    main()
