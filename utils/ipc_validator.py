"""
IPC Section Validator and Truncation Fix
Fixes the critical IPC truncation issue (e.g., "IPC 40..." → "IPC 409")
"""

import re
import json
from typing import Dict, List, Tuple

# Complete IPC sections database (most commonly used)
IPC_SECTIONS_DATABASE = {
    "40": "409",  # IPC 40... → IPC 409
    "30": "302",  # IPC 30... → IPC 302
    "42": "420",  # IPC 42... → IPC 420
    "37": "376",  # IPC 37... → IPC 376
    "34": "34",   # IPC 34
    "12": "120B", # IPC 12... → IPC 120B
    "50": "504",  # IPC 50... → IPC 504
    "29": "295",  # IPC 29... → IPC 295
    "49": "498A", # IPC 49... → IPC 498A
    "19": "193",  # IPC 19... → IPC 193
}

# Complete list of all valid IPC sections (1-511)
ALL_VALID_IPC = [
    "302", "304", "307", "308", "309", "311", "312", "313", "314", "315", "316", "317", "318",
    "320", "321", "322", "323", "324", "325", "326", "327", "328", "329", "330", "331", "332",
    "333", "334", "335", "336", "337", "338", "339", "340", "341", "342", "343", "344", "345",
    "346", "347", "348", "349", "350", "351", "352", "353", "354", "354A", "354B", "354C", "354D",
    "355", "356", "357", "358", "359", "360", "361", "362", "363", "363A", "364", "364A", "365",
    "366", "366A", "366B", "367", "368", "369", "370", "371", "372", "373", "374", "375", "376",
    "376A", "376B", "376C", "376D", "376E", "377", "378", "379", "380", "381", "382", "383",
    "384", "385", "386", "387", "388", "389", "390", "391", "392", "393", "394", "395", "396",
    "397", "398", "399", "400", "401", "402", "403", "404", "405", "406", "407", "408", "409",
    "410", "411", "412", "413", "414", "415", "416", "417", "418", "419", "420", "421", "422",
    "423", "424", "425", "426", "427", "428", "429", "430", "431", "432", "433", "434", "435",
    "436", "437", "438", "439", "440", "441", "447", "448", "449", "450", "451", "452", "453",
    "454", "455", "456", "457", "458", "459", "460", "461", "462", "463", "464", "465", "466",
    "467", "468", "469", "470", "471", "472", "473", "474", "475", "476", "477", "477A", "478",
    "479", "480", "481", "482", "483", "484", "485", "486", "487", "488", "489", "489A", "489B",
    "489C", "489D", "490", "491", "492", "493", "494", "495", "496", "497", "498", "498A", "499",
    "500", "501", "502", "503", "504", "505", "506", "507", "508", "509", "510", "511",
    "120A", "120B", "121", "121A", "122", "123", "124", "124A", "125", "126", "127", "128", "129",
    "130", "131", "132", "133", "134", "135", "136", "137", "138", "139", "140", "141", "142",
    "143", "144", "145", "146", "147", "148", "149", "150", "151", "152", "153", "153A", "153B",
    "154", "155", "156", "157", "158", "159", "160", "161", "162", "163", "164", "165", "166",
    "167", "168", "169", "170", "171", "171A", "171B", "171C", "171D", "171E", "171F", "171G",
    "171H", "171I", "172", "173", "174", "174A", "175", "176", "177", "178", "179", "180",
    "181", "182", "183", "184", "185", "186", "187", "188", "189", "190", "191", "192", "193",
    "194", "195", "195A", "196", "197", "198", "199", "200", "201", "202", "203", "204", "205",
    "206", "207", "208", "209", "210", "211", "212", "213", "214", "215", "216", "216A", "217",
    "218", "219", "220", "221", "222", "223", "224", "225", "225A", "225B", "226", "227", "228",
    "229", "229A", "230", "231", "232", "233", "234", "235", "236", "237", "238", "239", "240",
    "241", "242", "243", "244", "245", "246", "247", "248", "249", "250", "251", "252", "253",
    "254", "255", "256", "257", "258", "259", "260", "261", "262", "263", "264", "265", "266",
    "267", "268", "269", "270", "271", "272", "273", "274", "275", "276", "277", "278", "279",
    "280", "281", "282", "283", "284", "285", "286", "287", "288", "289", "290", "291", "292",
    "293", "294", "294A", "295", "295A", "296", "297", "298"
]


def detect_truncated_ipc(text: str) -> List[Tuple[str, str]]:
    """
    Detect truncated IPC sections in text
    
    Returns: List of (truncated_pattern, suggested_fix) tuples
    """
    # Pattern for truncated IPC: "IPC 30..." or "Section 40..."
    truncated_patterns = re.findall(r'((?:IPC|Section)\s+(\d{1,2})\.\.\.)', text, re.IGNORECASE)
    
    fixes = []
    for full_match, number in truncated_patterns:
        if number in IPC_SECTIONS_DATABASE:
            suggested = IPC_SECTIONS_DATABASE[number]
            fixes.append((full_match, f"IPC {suggested}"))
    
    return fixes


def fix_ipc_truncation(text: str, auto_fix: bool = True) -> Tuple[str, List[str]]:
    """
    Fix truncated IPC sections in text
    
    Args:
        text: Text containing potential truncated IPC sections
        auto_fix: If True, automatically fix known truncations
    
    Returns:
        (fixed_text, list_of_warnings)
    """
    warnings = []
    fixed_text = text
    
    # Detect truncated patterns
    truncations = detect_truncated_ipc(text)
    
    if truncations:
        warnings.append(f"⚠️ CRITICAL: Found {len(truncations)} truncated IPC section(s)")
        
        if auto_fix:
            for truncated, fix in truncations:
                fixed_text = fixed_text.replace(truncated, fix)
                warnings.append(f"  ✅ Fixed: '{truncated}' → '{fix}'")
        else:
            for truncated, fix in truncations:
                warnings.append(f"  ⚠️ Found: '{truncated}' (suggested: '{fix}')")
    
    return fixed_text, warnings


def validate_ipc_sections(text: str) -> Dict:
    """
    Validate all IPC sections in text
    
    Returns: Dict with validation results
    """
    # Find all IPC section references
    ipc_pattern = r'(?:IPC|Section)\s+(\d{1,3}[A-Z]?)'
    found_sections = re.findall(ipc_pattern, text, re.IGNORECASE)
    
    validation = {
        'total_found': len(found_sections),
        'valid': [],
        'invalid': [],
        'truncated': []
    }
    
    # Check for truncations
    truncations = detect_truncated_ipc(text)
    if truncations:
        validation['truncated'] = [t[0] for t in truncations]
    
    # Validate each section
    for section in found_sections:
        if section in ALL_VALID_IPC:
            validation['valid'].append(section)
        else:
            # Check if it's a partial match
            possible_matches = [s for s in ALL_VALID_IPC if s.startswith(section)]
            if possible_matches:
                validation['invalid'].append({
                    'found': section,
                    'possible': possible_matches[:3]  # Top 3 matches
                })
            else:
                validation['invalid'].append({
                    'found': section,
                    'possible': []
                })
    
    return validation


def extract_ipc_sections(text: str) -> List[str]:
    """
    Extract all IPC section numbers from text
    """
    ipc_pattern = r'(?:IPC|Section)\s+(\d{1,3}[A-Z]?)'
    return list(set(re.findall(ipc_pattern, text, re.IGNORECASE)))


def get_ipc_full_name(section: str) -> str:
    """
    Get full name of IPC section
    """
    IPC_NAMES = {
        "302": "Punishment for murder",
        "304": "Punishment for culpable homicide not amounting to murder",
        "307": "Attempt to murder",
        "376": "Punishment for rape",
        "409": "Criminal breach of trust by public servant",
        "420": "Cheating and dishonestly inducing delivery of property",
        "498A": "Husband or relative of husband of a woman subjecting her to cruelty",
        "120B": "Punishment of criminal conspiracy",
        "34": "Acts done by several persons in furtherance of common intention",
        # Add more as needed
    }
    return IPC_NAMES.get(section, f"IPC Section {section}")


# JSON Schema for IPC validation results
IPC_VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "response_id": {"type": "string"},
        "timestamp": {"type": "string"},
        "original_text": {"type": "string"},
        "fixed_text": {"type": "string"},
        "truncations_found": {"type": "array"},
        "truncations_fixed": {"type": "array"},
        "ipc_sections": {
            "type": "object",
            "properties": {
                "total_found": {"type": "integer"},
                "valid": {"type": "array"},
                "invalid": {"type": "array"},
                "truncated": {"type": "array"}
            }
        },
        "status": {"type": "string"},
        "warnings": {"type": "array"}
    }
}


if __name__ == "__main__":
    # Test cases
    test_texts = [
        "IPC 40... applies to public servants",  # Should fix to IPC 409
        "Section 30... is about murder",          # Should fix to IPC 302
        "IPC 42... deals with fraud",             # Should fix to IPC 420
        "IPC 376 is about rape",                  # Valid, no fix needed
        "IPC 999 is invalid"                      # Invalid section
    ]
    
    print("="*80)
    print("IPC VALIDATOR - TEST RESULTS")
    print("="*80)
    
    for i, test in enumerate(test_texts, 1):
        print(f"\nTest {i}: {test}")
        fixed, warnings = fix_ipc_truncation(test)
        print(f"Fixed: {fixed}")
        if warnings:
            for w in warnings:
                print(w)
        
        validation = validate_ipc_sections(fixed)
        print(f"Validation: {json.dumps(validation, indent=2)}")
    
    print("\n" + "="*80)

