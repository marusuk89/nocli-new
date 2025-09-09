import xml.etree.ElementTree as ET

def strip_namespace(tree: ET.ElementTree) -> ET.Element:
    root = tree.getroot()
    for elem in root.iter():
        if isinstance(elem.tag, str) and '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]
    return root

def remove_empty_lines_from_str(xml_str: str) -> str:
    return "\n".join(line for line in xml_str.splitlines() if line.strip())