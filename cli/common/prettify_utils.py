import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

def prettify_xml(elem: ET.Element) -> str:
    """ElementTree Element를 들여쓰기 적용된 문자열(XML)로 변환"""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")