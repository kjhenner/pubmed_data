from lxml import etree
from datetime import datetime
import md5
import os
import csv

def time_millis(date):
    return str(int((date - datetime.utcfromtimestamp(0)).total_seconds() * 1000.0))

def parse_date(elem):
    if not elem:
        return ''
    elem = elem[0]
    year = elem.xpath('year')[0].text
    month = text_if_xpath(elem, 'month') or '1'
    day = text_if_xpath(elem, 'day') or '1'
    return time_millis(datetime(int(year), int(month), int(day)))

def write_csv_headers(output_dir):
    headers = {
        'journals': 'nlm_ta,jr_title',
        'articles': 'pmid,nlm_ta,pmc,doi,title,volume,fpage,lpage,epub_date,ppub_date,pmc_release_date,nihms_submitted_date,abstract',
        'ext_journals': 'nlm_ta',
        'ext_articles': 'pmid,nlm_ta,doi,title,volume',
        'contribs': 'id,given_names,surname',
        'paragraphs': 'id,text',
        'contributed': 'START_ID,contrib_type,END_ID,TYPE',
        'contains': 'START_ID,END_ID,TYPE',
        'cites': 'START_ID,END_ID,TYPE',
        'published': 'START_ID,END_ID,TYPE',
    }
    for table in headers.keys():
        with open(os.path.join(output_dir, table + '.csv'), 'wb') as f:
            f.write(headers[table] + "\n")

def flush_buffer(data_buffer, output_dir):
    for table in data_buffer.keys():
        append_to_csv(data_buffer[table], table, output_dir)

def append_to_csv(rows, table_name, output_dir):
    with open(os.path.join(output_dir, table_name + '.csv'), 'ab') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        for row in rows:
            csv_writer.writerow([text.encode("utf8") for text in row])

def to_table_rows(data):
    table_rows = {
        'journals': [
            [
                journal['nlm-ta'],
                journal['jr-title'],
            ]
            for journal in data['journals']
        ],
        'ext_journals': [
            [
                journal['nlm-ta'],
            ]
            for journal in data['ext_journals']
        ],
        'articles': [
            [
                article['pmid'],
                article['nlm-ta'],
                article['pmc'],
                article['doi'],
                article['title'],
                article['volume'],
                article['fpage'],
                article['lpage'],
                article['epub-date'],
                article['ppub-date'],
                article['pmc-release-date'],
                article['nihms-submitted-date'],
                article['abstract'],
            ]
            for article in data['articles']
        ],
        'ext_articles': [
            [
                article['pmid'],
                article['nlm-ta'],
                article['doi'],
                article['title'],
                article['volume'],
            ]
            for article in data['ext_articles']
        ],
        'contribs': [
            [
                contrib['given-names'] + ' ' + contrib['surname'],
                contrib['given-names'],
                contrib['surname'],
            ]
            for contrib in data['contribs']
        ],
        'paragraphs': [
            [
                paragraph['id'],
                paragraph['text'],
            ]
            for paragraph in data['paragraphs']
        ],
        'contributed': [
            [
                contrib['given-names'] + ' ' + contrib['surname'],
                contrib['contrib-type'],
                data['pmid'],
            ]
            for contrib in data['contribs']
        ],
        'contains': [
            [
                data['pmid'],
                paragraph['id'],
            ]
            for paragraph in data['paragraphs']
        ],
        'cites': [
            [
                paragraph['id'],
                ref,
            ]
            for paragraph in data['paragraphs'] for ref in paragraph['ref-pmids']
        ],
        'published': [[
            data['nlm-ta'],
            data['pmid'],
        ]],
    }
    return table_rows

def parse_directory(data_dir, data_buffer):
    subdirs = os.listdir(data_dir)
    for subdir in subdirs:
        print(subdir)
        if os.path.isdir(os.path.join(data_dir, subdir)):
            filepaths = os.listdir(os.path.join(data_dir, subdir))
            print('processing ' + str(len(filepaths)) + ' files in ' + subdir)
            for filepath in filepaths:
                table_rows = parse_file(os.path.join(data_dir, subdir, filepath))
                for key in table_rows.keys():
                    if key in data_buffer:
                        data_buffer[key] += table_rows[key]
                    else:
                        data_buffer[key] = table_rows[key]

def text_if_xpath(element, xpath):
    at_xpath = element.xpath(xpath)
    if len(at_xpath):
        return at_xpath[0].text
    else:
        return ''

def itertext_if_xpath(element, xpath):
    at_xpath = element.xpath(xpath)
    if len(at_xpath):
        return ''.join(at_xpath[0].itertext())
    else:
        return ''

def if_xpath(element, xpath):
    at_xpath = element.xpath(xpath)
    if len(at_xpath):
        return at_xpath[0]
    else:
        return ''

def parse_file(path):

    data = {
        'refs': {},
        'paragraphs': [],
        'contribs': [],
        'ext_contribs': [],
        'journals': [],
        'articles': [],
        'ext_journals': [],
        'ext_articles': []
    }

    #Parse the XML and get the tree and root
    tree = etree.parse(path)
    root = tree.getroot()

    # /article
    article = root.xpath('/article')[0]

    # Parse the back first so we can include ref pmids in the paragraph data
    # itself.
    # /article/back
    back = if_xpath(article, 'back')
    if back:
        for ref in back.xpath('ref-list/ref'):
            # Some articles have citation metadata nested under an additional
            # element, so we use 'descendant-or-self::' in the following xpaths
            pmid = text_if_xpath(ref, "descendant-or-self::*/pub-id[@pub-id-type='pmid']")
            ref_id = ref.xpath('@id')[0]
            # Map ref_ids to the matching PMID.
            data['refs'][ref_id] = pmid
            nlm_ta = itertext_if_xpath(ref, "descendant-or-self::*/source")
            data['ext_journals'].append({
                'nlm-ta': nlm_ta,
            })
            data['ext_articles'].append({
                'pmid': pmid,
                'nlm-ta': nlm_ta,
                'doi': text_if_xpath(ref, "descendant-or-self::*/pub-id[@pub-id-type='pmid']"),
                'title': itertext_if_xpath(ref, 'descendant-or-self::*/article-title'),
                'volume': text_if_xpath(ref, 'descendant-or-self::*/volume'),
            })

    # /article/front
    front = article.xpath('front')[0]

    # /article/front/journal-meta
    journal_meta = front.xpath('journal-meta')[0]
    data['nlm-ta'] = text_if_xpath(journal_meta, "journal-id[@journal-id-type='nlm-ta']")
    data['journals'].append({
        'nlm-ta': data['nlm-ta'],
        'jr-title': journal_meta.xpath("journal-title-group/journal-title|journal-title")[0].text
    })

    # /article/front/article-meta
    article_meta = front.xpath('article-meta')[0]

    pmc_release_date = article_meta.xpath("pub-date[@pub-type='pmc-release']")
    epub_date = article_meta.xpath("pub-date[@pub-type='epub']")
    ppub_date = article_meta.xpath("pub-date[@pub-type='ppub']")
    nihms_submitted_date = article_meta.xpath("pub-date[@pub-type='nihms-submitted']")
    data['pmid'] = text_if_xpath(article_meta, "article-id[@pub-id-type='pmid']")

    data['articles'].append({
        'manuscript_id': text_if_xpath(article_meta, "article-id[@pub-id-type='manuscript']"),
        'pmid': data['pmid'],
        'nlm-ta': data['nlm-ta'],
        'pmc': text_if_xpath(article_meta, "article-id[@pub-id-type='pmc']"),
        'doi': text_if_xpath(article_meta, "article-id[@pub-id-type='doi']"),
        'title': ''.join(article_meta.xpath('title-group/article-title')[0].itertext()),
        'volume': text_if_xpath(article_meta, 'volume'),
        'issue': text_if_xpath(article_meta, 'issue'),
        'fpage': text_if_xpath(article_meta, 'fpage'),
        'lpage': text_if_xpath(article_meta, 'lpage'),
        'abstract': itertext_if_xpath(article_meta, 'abstract'),
        'pmc-release-date': parse_date(pmc_release_date),
        'epub-date': parse_date(epub_date),
        'ppub-date': parse_date(ppub_date),
        'nihms-submitted-date': parse_date(nihms_submitted_date)
    })

    # /article/front/article-meta/contrib-group
    contrib_group = article_meta.xpath('contrib-group')[0]
    contribs = contrib_group.xpath('contrib')
    for contrib in contribs:
        contrib_type = contrib.get('contrib-type')
        # The name may or may not be nested in a name element!
        name = contrib.xpath('name')
        if len(name):
            contrib = name[0]
        data['contribs'].append({
            'contrib-type': contrib_type,
            'surname': text_if_xpath(contrib, 'surname') ,
            'given-names': text_if_xpath(contrib, 'given-names|given-name'),
        })

    # /articls/body
    body = article.xpath('body')[0]
    for paragraph in body.xpath('*//p'):
        # xrefs may be nested in zero or more formatting tags
        # collect xrefs with bibr class and all xrefs as two separate lists
        # because we want to remove all xrefs from the tree to clean up
        # paragraph text but we only want to include bibr class xrefs in
        # the parsed data.
        bib_refs = paragraph.xpath("descendant-or-self::*/xref[@ref-type='bibr']")
        xrefs = paragraph.xpath('descendant-or-self::*/xref')
        #after collecting xrefs, remove them from the tree to
        #clean up paragraph text.
        for xref in xrefs:
            xref.getparent().remove(xref)
        text = "".join(paragraph.itertext())
        data['paragraphs'].append({
            'ref-pmids': [data['refs'][bibr.xpath('@rid')[0]] for bibr in bib_refs],
            'text': text,
            'id': md5.new(text.encode('utf-8')).hexdigest(),
        })

    return to_table_rows(data)
