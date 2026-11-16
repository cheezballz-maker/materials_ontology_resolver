"""Evaluate explicitly scoped evidence without opening a canonical registry."""

from dataclasses import asdict, dataclass
from hashlib import sha256
import json

from canonical_registry.chemistry import describe
from canonical_registry.chemical_concept_registry.constraints import molecular
from canonical_registry.chemical_concept_registry.identity_contract import supported_definition

POLICY = "chemical-identity-evidence-sufficiency-v1"
WHOLE = "WHOLE_REFERENT"
SCOPES = {WHOLE,"CONSTITUENT","PRECURSOR","RELATED_MATERIAL","SCOPE_UNESTABLISHED"}


def digest(value):
    return sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()


@dataclass(frozen=True)
class Claim:
    claim_id: str
    kind: str
    value: str
    scope: str
    entity: str
    authority: str
    grants: tuple[str, ...]
    document: str
    locator: str
    revision: str
    namespace: str = ""
    identity_scope: str = ""
    binding_revision: str = ""

    def qualified(self, *grants):
        return (isinstance(self.value,str) and all((self.value.strip(),self.authority,self.document,
                self.locator,self.revision,self.entity)) and set(grants)<=set(self.grants))


@dataclass(frozen=True)
class Evidence:
    referent: str
    source_reference: str
    source_revision: str
    designation: str
    claims: tuple[Claim, ...]
    material_scope: str = "UNESTABLISHED"
    scope_evidence: tuple[str, ...] = ()
    holds: tuple[str, ...] = ()


def structure_signature(g):
    return (g["smiles"],g["inchi"],g["inchikey"],g["fixed_h_inchi"])


class Evaluator:
    def __init__(self, official_validator):
        self.official_validator = official_validator
        self.validated = {}
        self.official = {}

    def _graph(self, claim):
        k = claim.kind,claim.value
        if k not in self.validated:
            if len(claim.value)>1200:
                raise ValueError("STRUCTURAL_INPUT_LIMIT")
            self.validated[k] = describe(claim.value,claim.kind.lower())
        return self.validated[k]

    def evaluate(self, e):
        claims = e.claims
        if (not all((e.referent,e.source_reference,e.source_revision)) or
                len({c.claim_id for c in claims})!=len(claims) or
                any(not c.claim_id or c.scope not in SCOPES for c in claims)):
            raise ValueError("Invalid evidence packet or claim identity")
        base = {"policy_version":POLICY,"evidence_version":digest(asdict(e)),"referent":e.referent,
                "source_reference":e.source_reference,"source_revision":e.source_revision,
                "evidence_pathway":None,"resolution_pathway":None,"supporting_claim_ids":[],
                "scope":"SCOPE_UNESTABLISHED","specificity":None,
                "authority_assessment":[{"id":c.claim_id,"scope":c.scope,"authority":c.authority,
                  "qualified_grants":list(c.grants) if c.qualified() else []} for c in claims]}

        def finish(status,reasons,**extra):
            return {**base,"eligibility":status,"reasons":list(reasons),**extra}

        def bound(claim, grant):
            return (claim.scope==WHOLE and claim.qualified(grant,"REFERENT")
                    and (claim.binding_revision or claim.revision)==e.source_revision)

        if e.holds:
            return finish("REVIEW_HOLD",e.holds)
        if e.material_scope in {"VARIABLE","MIXTURE","POLYMER","PREPARATION","BROAD"} and e.scope_evidence:
            relevant = {"SMILES":"STRUCTURE","INCHI":"STRUCTURE","NOMENCLATURE_LINK":"NOMENCLATURE",
                        "IDENTIFIER_LINK":"IDENTIFIER"}
            if any(c.kind in relevant and bound(c,relevant[c.kind]) for c in claims):
                return finish("REVIEW_HOLD",("DISCRETE_STRUCTURE_CONTRADICTS_SOURCE_MATERIAL_SCOPE",))
            return finish("NOT_APPLICABLE_TO_EXACT_MOLECULAR_RESOLUTION",("SOURCE_ATTESTED_NONDISCRETE_SCOPE",),
                          scope="SOURCE_ATTESTED_NONDISCRETE")

        paths = {}
        for c in claims:
            if c.scope!=WHOLE:
                continue
            if c.kind in {"SMILES","INCHI"} and bound(c,"STRUCTURE"):
                paths.setdefault(c.entity,[]).append(("A_DIRECT_STRUCTURE",c))
            elif c.kind=="NOMENCLATURE_LINK" and bound(c,"NOMENCLATURE"):
                paths.setdefault(c.entity,[]).append(("B_NOMENCLATURE",c))
            elif (c.kind=="IDENTIFIER_LINK" and c.namespace and c.identity_scope in {"DEFINED_CHEMICAL","MOLECULAR_PARTIAL"}
                  and bound(c,"IDENTIFIER")):
                paths.setdefault(c.entity,[]).append(("C_IDENTIFIER",c))
        if not paths:
            reason = "WHOLE_REFERENT_BINDING_UNESTABLISHED" if any(c.kind in {"SMILES","INCHI"} for c in claims) else "NO_SUFFICIENT_EVIDENCE_PATH"
            return finish("NEEDS_MORE_EVIDENCE",(reason,))

        if len(paths)!=1:
            return finish("REVIEW_HOLD",("COMPETING_QUALIFIED_WHOLE_REFERENTS",))
        entity,links = next(iter(paths.items()))
        structural = [c for c in claims if c.entity==entity and c.kind in {"SMILES","INCHI"} and
                      c.scope in {WHOLE,"SCOPE_UNESTABLISHED"} and c.qualified("STRUCTURE")]
        if not structural:
            return finish("NEEDS_MORE_EVIDENCE",("QUALIFIED_STRUCTURE_MISSING",),scope=WHOLE)
        try:
            graphs = [self._graph(c) for c in structural]
        except (ValueError,RuntimeError) as exc:
            return finish("REVIEW_HOLD",("QUALIFIED_STRUCTURE_INVALID",),scope=WHOLE,diagnostic=str(exc))
        if len({structure_signature(g) for g in graphs})!=1:
            return finish("REVIEW_HOLD",("QUALIFIED_STRUCTURES_DIFFER_OR_REPRESENTATION_UNRESOLVED",),scope=WHOLE)
        g = graphs[0]
        for c in claims:
            if c.entity!=entity or c.scope not in {WHOLE,"SCOPE_UNESTABLISHED"} or not c.qualified("STRUCTURE"):
                continue
            if ((c.kind=="INCHIKEY" and c.value!=g["inchikey"]) or
                    (c.kind=="FORMULA" and c.value!=g["formula"])):
                return finish("REVIEW_HOLD",("QUALIFIED_STRUCTURE_DESCRIPTOR_DISAGREES",),scope=WHOLE)
        if not g["fixed_h_inchi"] or g["atoms"]>100:
            return finish("NEEDS_MORE_EVIDENCE",("STRUCTURAL_SCOPE_UNSUPPORTED",),scope=WHOLE)
        if g["components"]>1 and not any(c.qualified("COMPLETE_COMPOSITION") for c in structural):
            return finish("NEEDS_MORE_EVIDENCE",("COMPONENT_COMPOSITION_UNQUALIFIED",),scope=WHOLE)
        open_stereo = any(s["specified"]!="Specified" for s in g["stereo"])
        partial = [c for c in claims if c.kind=="STEREO_SCOPE" and c.entity==entity and c.scope==WHOLE and
                   c.value=="EXPLICITLY_UNSPECIFIED" and bound(c,"SPECIFICATION")]
        route = "SUBSTANCE"
        definition = None
        warnings = {w.strip() for w in g["inchi_warning"].split(";") if w.strip()}
        if open_stereo:
            if not partial:
                return finish("NEEDS_MORE_EVIDENCE",("UNSPECIFIED_STEREO_NOT_SOURCE_DEFINED",),scope=WHOLE)
            try:
                definition = molecular(g["smiles"],"EXPLICITLY_UNSPECIFIED")
                definition["stereo_state"] = "EXPLICITLY_UNSPECIFIED"
                if not supported_definition(definition):
                    raise ValueError("SOURCE_PARTIAL_DEFINITION_CONTRACT_REJECTED")
            except (ValueError,RuntimeError) as exc:
                return finish("NEEDS_MORE_EVIDENCE",("PARTIAL_MOLECULAR_DEFINITION_UNSUPPORTED",),scope=WHOLE,diagnostic=str(exc))
            route = "CHEMICAL_CONCEPT"
            warnings.discard("Omitted undefined stereo")
        elif partial or any(c.identity_scope=="MOLECULAR_PARTIAL" for _,c in links):
            return finish("REVIEW_HOLD",("SOURCE_PARTIAL_SCOPE_CONTRADICTS_GRAPH",),scope=WHOLE)
        if warnings:
            return finish("REVIEW_HOLD",("INCHI_WARNING_REQUIRES_REVIEW",),scope=WHOLE,warnings=sorted(warnings))
        k = structure_signature(g)
        if k not in self.official:
            try:
                self.official[k] = self.official_validator(g)
            except (ValueError,RuntimeError,OSError) as exc:
                self.official[k] = {"status":"ERROR","diagnostic":type(exc).__name__}
        proof = self.official[k]
        if (proof.get("status") not in {"SUCCESS","WARNING"} or not proof.get("agrees") or
                proof.get("inchi")!=g["inchi"] or proof.get("inchikey")!=g["inchikey"]):
            return finish("REVIEW_HOLD",("OFFICIAL_INCHI_UNCONFIRMED",),scope=WHOLE,official_validation=proof)
        return finish("CANDIDATE_READY",("QUALIFIED_WHOLE_REFERENT_AND_VALIDATED_GRAPH",),
                      scope=WHOLE,evidence_pathway=min(p for p,_ in links),resolution_pathway=route,
                      supporting_claim_ids=sorted({c.claim_id for c in structural+partial} | {c.claim_id for _,c in links}),
                      specificity={**{key:g[key] for key in ("smiles","fixed_h_inchi","inchi","inchikey","formula",
                          "charge","components","stereo","isotopes","radicals")},"partial_definition":definition},
                      official_validation=proof)
