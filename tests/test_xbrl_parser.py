from pathlib import Path

import pytest
from rich import print

from edgar import Filing
from edgar.xbrl.parser import (parse_labels, parse_calculation, parse_definitions, XBRLData,
                               XBRLInstance, XBRLPresentation, FinancialStatement)

# Sample XML strings for testing
SAMPLE_INSTANCE_XML = """
<xbrl xml:lang="en-US"
      xmlns="http://www.xbrl.org/2003/instance"
      xmlns:dei="http://xbrl.sec.gov/dei/2023"
      xmlns:us-gaap="http://fasb.org/us-gaap/2023">
    <context id="ctx1">
        <entity><identifier>1234567890</identifier></entity>
        <period>
            <startDate>2023-01-01</startDate>
            <endDate>2023-12-31</endDate>
        </period>
    </context>
    <us-gaap:Assets contextRef="ctx1" unitRef="usd" decimals="-6">1000000</us-gaap:Assets>
    <us-gaap:Liabilities contextRef="ctx1" unitRef="usd" decimals="-6">500000</us-gaap:Liabilities>
    <dei:DocumentPeriodEndDate contextRef="ctx1">2023-12-31</dei:DocumentPeriodEndDate>
</xbrl>
"""

SAMPLE_PRESENTATION_XML = """
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:xlink="http://www.w3.org/1999/xlink"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xsi:schemaLocation="http://www.xbrl.org/2003/linkbase http://www.xbrl.org/2003/xbrl-linkbase-2003-12-31.xsd">
<link:roleRef roleURI="http://www.company.com/role/CONSOLIDATEDBALANCESHEETS" xlink:type="simple" xlink:href="aapl-20230930.xsd#CoverPage"/>
<link:presentationLink xlink:role="http://www.company.com/role/CONSOLIDATEDBALANCESHEETS">
    <link:loc xlink:label="loc_assets" xlink:href="#us-gaap_Assets"/>
    <link:loc xlink:label="loc_liabilities" xlink:href="#us-gaap_Liabilities"/>
    <link:presentationArc xlink:from="assets" xlink:to="liabilities" order="1"/>
</link:presentationLink>
</link:linkbase>
"""


@pytest.fixture
def sample_instance():
    return XBRLInstance.parse(SAMPLE_INSTANCE_XML)


@pytest.fixture
def sample_presentation():
    return XBRLPresentation.parse(SAMPLE_PRESENTATION_XML)


@pytest.fixture
def sample_labels():
    return {
        'us-gaap_Assets': {'label': 'Assets'},
        'us-gaap_Liabilities': {'label': 'Liabilities'}
    }


@pytest.fixture
def sample_calculations():
    return {}


def test_xbrl_instance_parsing(sample_instance):
    assert len(sample_instance.facts) == 3
    assert sample_instance.get_document_period() == '2023-12-31'


def test_xbrl_instance_query_facts(sample_instance):
    assets = sample_instance.query_facts(concept='us-gaap:Assets')
    assert len(assets) == 1
    assert assets.iloc[0]['value'] == '1000000'


def test_xbrl_presentation_parsing(sample_presentation):
    assert len(sample_presentation.roles) == 1
    role = "http://www.company.com/role/CONSOLIDATEDBALANCESHEETS"
    assert role in sample_presentation.roles
    assert len(sample_presentation.roles[role].children) == 2


def test_financial_statement_creation(sample_instance, sample_presentation, sample_labels, sample_calculations):
    role = "http://www.company.com/role/CONSOLIDATEDBALANCESHEETS"
    statement = FinancialStatement.create(
        "Balance Sheet",
        sample_presentation.roles[role],
        sample_labels,
        sample_calculations,
        sample_instance
    )
    assert statement.name == "Balance Sheet"
    assert len(statement.line_items) == 2


def test_xbrl_parser_get_financial_statement(sample_instance, sample_presentation, sample_labels, sample_calculations):
    parser = XBRLData(
        instance=sample_instance,
        presentation=sample_presentation,
        labels=sample_labels,
        calculations=sample_calculations
    )
    parser.parse_financial_statements()

    df = parser.get_statement("CONSOLIDATEDBALANCESHEETS")
    assert df is not None
    assert 'Assets' in df.index
    assert 'Liabilities' in df.index
    assert 'Q4 2023' in df.columns


def test_xbrl_parser_get_balance_sheet(sample_instance, sample_presentation, sample_labels, sample_calculations):
    xbrl = XBRLData(
        instance=sample_instance,
        presentation=sample_presentation,
        labels=sample_labels,
        calculations=sample_calculations
    )
    xbrl.parse_financial_statements()

    df = xbrl.get_balance_sheet()
    assert df is not None
    assert 'Assets' in df.index
    assert 'Liabilities' in df.index
    assert 'Q4 2023' in df.columns


@pytest.mark.asyncio
async def test_xbrl_parser_from_filing():
    filing = Filing(company='Accenture plc', cik=1467373, form='10-K', filing_date='2023-10-12',
                    accession_no='0001467373-23-000324')

    parser = await XBRLData.from_filing(filing)
    assert isinstance(parser, XBRLData)
    assert isinstance(parser.instance, XBRLInstance)
    assert isinstance(parser.presentation, XBRLPresentation)


def test_parse_xbrl_presentation():
    presentation = XBRLPresentation.parse(Path('data/xbrl/datafiles/aapl/aapl-20230930_pre.xml').read_text())
    _repr_ = repr(presentation)
    print(_repr_)
    assert "EntitiesTable" in _repr_
    assert "A1.375NotesDue2024Member" in _repr_


def test_xbrl_presentation_get_structure_for_role():
    presentation = XBRLPresentation.parse(Path('data/xbrl/datafiles/aapl/aapl-20230930_pre.xml').read_text())
    structure = presentation.get_structure('http://www.apple.com/role/CONSOLIDATEDSTATEMENTSOFOPERATIONS')
    assert structure
    print(structure)


def test_xbrl_presentation_list_roles():
    presentation = XBRLPresentation.parse(Path('data/xbrl/datafiles/aapl/aapl-20230930_pre.xml').read_text())
    roles = presentation.list_roles()
    assert 'http://www.apple.com/role/Leases' in roles


def test_parse_labels():
    labels = parse_labels(Path('data/xbrl/datafiles/aapl/aapl-20230930_lab.xml').read_text())
    assert labels['us-gaap_ResearchAndDevelopmentExpense']['label'] == 'Research and Development Expense'


def test_parse_calculations():
    calculations = parse_calculation(Path('data/xbrl/datafiles/aapl/aapl-20230930_cal.xml').read_text())
    assert calculations
    assert calculations['http://www.apple.com/role/CONSOLIDATEDSTATEMENTSOFOPERATIONS']


def test_parse_definitions():
    definitions = parse_definitions(Path('data/xbrl/datafiles/aapl/aapl-20230930_def.xml').read_text())
    assert definitions

@pytest.mark.asyncio
async def test_get_shareholder_equity_statement():
    filing: Filing = Filing(company='Apple Inc.', cik=320193, form='10-K', filing_date='2023-11-03',
                            accession_no='0000320193-23-000106')
    xbrl_data = await XBRLData.from_filing(filing)
    statement = xbrl_data.get_balance_sheet(include_format_info=True)