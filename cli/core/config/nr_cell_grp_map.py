nr_cell_grp_template_map = {
  "AEQN_4_2": "typeC",
  "AEQY_4_2": "typeC",
  "AHQK_2_2": "typeA",
  "AHQK_4_2": "typeB",
  "AHQK_4_4": "typeA",
  "APHA_4_2": "typeA",
  "AQQA_4_2": "typeC",
  "AZQG_2_2_0": "typeA",
  "AZQG_2_2_4": "typeD",
  "AZQG_4_2_0": "typeA",
  "AZQG_4_2_2": "typeB",
  "AZQG_4_4": "typeA",
  "AZQS_2_2_0": "typeA",
  "AZQS_2_2_4": "typeD",
  "AZQS_4_2_0": "typeA",
  "AZQS_4_2_2": "typeB",
  "AZQS_4_4": "typeA",

  "DEFAULT": "typeA"
}

def resolve_nrcell_grp_template_key(ru_type: str) -> str:
    if not ru_type:
        return nr_cell_grp_template_map.get("DEFAULT")
    return nr_cell_grp_template_map.get(ru_type, nr_cell_grp_template_map.get("DEFAULT"))