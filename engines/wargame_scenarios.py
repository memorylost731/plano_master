#!/usr/bin/env python3
"""
Wargame Scenarios — Plausible multi-actor simulations for the MAJOIE v GAVRYUSHEVA case.

Each scenario involves real actors (as persona avatars) in realistic situations
derived from the case timeline. Used for:
  - Predicting adversary behavior
  - Testing legal strategies
  - Identifying vulnerabilities
  - Training Cael on tactical decision-making

All scenarios are based on documented events and plausible extrapolations.
"""

SCENARIOS = {
    # ================================================================
    # SCENARIO 1: Monaco Court Confrontation
    # Marina's legal team vs Hadrien's in a custody hearing
    # ================================================================
    "custody_hearing": {
        "name": "Monaco Custody Hearing — TPI",
        "description": (
            "A scheduled custody hearing at the Tribunal de Première Instance de Monaco. "
            "Marina's team (Patricia Rey) argues for sole custody. Hadrien's team presents "
            "evidence of non-présentation d'enfant and the Bermon relationship. "
            "Judge Barbier-Chassaing (or successor) presides."
        ),
        "personas": ["Marina", "Patricia Rey", "Christophe Sosso", "Françoise Barbier-Chassaing", "Constantin"],
        "stakes": "Custody of Constantin, pension modification, evidence admissibility",
        "variables": [
            "Does Marina's team challenge the Bermon evidence?",
            "Does Patricia Rey attempt to exclude WhatsApp screenshots?",
            "Does the judge allow the crypto forensic evidence?",
            "Does Constantin's own preference factor in (age-dependent)?",
        ],
        "game_theory": {
            "players": ["Marina's team", "Hadrien's team"],
            "strategies": {
                "Marina": ["full_denial", "partial_admission", "settlement_offer", "counter_attack"],
                "Hadrien": ["evidence_blitz", "gradual_disclosure", "settlement_accept", "escalate_criminal"],
            },
        },
    },

    # ================================================================
    # SCENARIO 2: Bermon Exposure
    # What happens when the Bermon-Marina relationship becomes public
    # ================================================================
    "bermon_exposure": {
        "name": "Captain Bermon Exposure",
        "description": (
            "Evidence of Captain Benoit Bermon's romantic/sexual relationship with Marina "
            "Gavryusheva (a suspect in multiple criminal cases he was involved in investigating) "
            "becomes known to the Monaco Sûreté hierarchy. "
            "How does each actor respond?"
        ),
        "personas": ["Benoit Bermon", "Marina", "Patricia Rey", "Ken Gamble"],
        "stakes": "Bermon's career, case integrity, obstruction of justice charges",
        "variables": [
            "Does Bermon deny or admit?",
            "Does Marina throw Bermon under the bus?",
            "Does the Sûreté initiate internal investigation?",
            "Does Ken Gamble/IFW use this for the crypto recovery case?",
        ],
        "game_theory": {
            "players": ["Bermon", "Marina", "Monaco Sûreté", "Hadrien"],
            "strategies": {
                "Bermon": ["deny_everything", "resign_quietly", "cooperate", "threaten_witnesses"],
                "Marina": ["protect_bermon", "sacrifice_bermon", "flee_jurisdiction"],
                "Sûreté": ["internal_investigation", "cover_up", "refer_to_prosecution"],
                "Hadrien": ["formal_complaint", "media_exposure", "leverage_for_settlement"],
            },
        },
    },

    # ================================================================
    # SCENARIO 3: Crypto Recovery Operation
    # IFW Global attempts to trace and recover hidden crypto assets
    # ================================================================
    "crypto_recovery": {
        "name": "IFW Crypto Recovery Operation",
        "description": (
            "Ken Gamble's IFW Global team (Ilana Katz TRM-CI, Simon Brock) executes "
            "a blockchain forensic operation to trace Marina's 163 BTC (Ledger #2) "
            "and 875K ATOM (Simply Staking). The operation requires cooperation across "
            "Monaco, Malta, and potentially Switzerland."
        ),
        "personas": ["Ken Gamble", "Marina", "Keith Balzan", "Franco Debono"],
        "stakes": "€42M+ in crypto assets, cross-border legal cooperation",
        "variables": [
            "Does Malta FIAU cooperate with the request?",
            "Does Marina move assets before they're frozen?",
            "Does Keith Balzan have access to any wallets?",
            "Does Swiss banking secrecy block the Frick/N26 inquiry?",
        ],
        "game_theory": {
            "players": ["IFW/Hadrien", "Marina", "Malta authorities", "Swiss banks"],
            "strategies": {
                "IFW": ["eio_request", "direct_exchange_freeze", "public_pressure", "private_negotiation"],
                "Marina": ["move_assets", "legal_challenge", "cooperate_partially", "destroy_evidence"],
                "Malta": ["full_cooperation", "partial_cooperation", "bureaucratic_delay", "refuse"],
                "Swiss": ["comply_with_court_order", "invoke_banking_secrecy", "negotiate"],
            },
        },
    },

    # ================================================================
    # SCENARIO 4: Keith Balzan Confrontation
    # What happens when Keith Balzan is directly confronted
    # ================================================================
    "balzan_confrontation": {
        "name": "Keith Balzan Confrontation in Malta",
        "description": (
            "Keith Balzan is confronted with evidence of his role in supporting "
            "Marina's asset concealment and obstruction. This could happen via "
            "Maltese police, IFW investigation, or direct legal proceedings."
        ),
        "personas": ["Keith Balzan", "Marina", "Franco Debono", "Ken Gamble"],
        "stakes": "Malta legal proceedings, asset access, witness cooperation",
        "variables": [
            "Does Balzan cooperate to save himself?",
            "Does Marina maintain loyalty to Balzan?",
            "Does Balzan have independent knowledge of asset locations?",
            "Does Franco Debono advise cooperation or resistance?",
        ],
        "game_theory": {
            "players": ["Balzan", "Marina", "Maltese police", "Hadrien's legal team"],
            "strategies": {
                "Balzan": ["full_cooperation", "silence", "blame_marina", "flee"],
                "Marina": ["support_balzan", "distance_from_balzan", "joint_defense"],
                "Police": ["arrest_and_interrogate", "surveillance", "ignore"],
                "Hadrien": ["offer_immunity_deal", "criminal_complaint", "civil_suit"],
            },
        },
    },

    # ================================================================
    # SCENARIO 5: Full Institutional Coalition
    # All legitimate institutional channels activated simultaneously
    # ================================================================
    "institutional_coalition": {
        "name": "Full Institutional Coalition Activation",
        "description": (
            "Simultaneous activation of all institutional channels: "
            "Monaco criminal complaints (assassination instigation, violence), "
            "Malta police task force, European Investigation Order (EIO), "
            "Swiss criminal procedure (chantage via MERKT Geneva), "
            "IFW Global crypto tracing, CPM victim support. "
            "This is the dominant strategy from the psych engine game theory."
        ),
        "personas": ["Marina", "Patricia Rey", "Keith Balzan", "Ken Gamble", "Benoit Bermon", "Franco Debono"],
        "stakes": "Criminal prosecution, asset recovery, custody, case resolution",
        "variables": [
            "Can Marina sustain defense on all fronts simultaneously?",
            "Does the institutional pressure cause internal fractures in her support network?",
            "Does Bermon's exposure cascade into other Monaco institutional failures?",
            "Is the probation constraint (2025-2028) a binding limitation?",
        ],
        "game_theory": {
            "players": ["Institutional coalition", "Marina's defense network"],
            "strategies": {
                "Coalition": ["synchronized_pressure", "sequential_escalation", "targeted_weakest_link"],
                "Defense": ["unified_resistance", "sacrifice_periphery", "settlement_negotiation", "flee_jurisdiction"],
            },
        },
    },
}

def list_scenarios():
    for key, s in SCENARIOS.items():
        print(f"  {key:<30} {s['name']}")
        print(f"    Players: {', '.join(s['personas'])}")
        print(f"    Stakes: {s['stakes']}")
        print()

if __name__ == "__main__":
    list_scenarios()
