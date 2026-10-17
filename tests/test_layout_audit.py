import fitz


def test_audit_flags_large_gap_but_not_normal_final_page(tmp_path):
    from auto_paper_reading.layout import audit_pdf
    p = tmp_path/'pages.pdf'
    d = fitz.open()
    d.new_page(width=595, height=842).insert_text((72, 100), 'Short page before a large image')
    d.new_page(width=595, height=842).insert_text((72, 100), 'Normal short final page')
    d.save(p)
    result = audit_pdf(p)
    assert result['pages'][0]['needs_review']
    assert result['pages'][0]['bottom_blank_pt'] > 600
    assert not result['pages'][1]['needs_review']


def test_image_area_counts_as_content_not_whitespace(tmp_path):
    from PIL import Image
    from auto_paper_reading.layout import audit_pdf
    image = tmp_path/'figure.png'
    Image.new('RGB', (300, 600), 'black').save(image)
    p = tmp_path/'illustrated.pdf'
    d = fitz.open()
    page = d.new_page(width=595, height=842)
    page.insert_image(fitz.Rect(120, 72, 420, 672), filename=str(image))
    page.insert_text((72, 700), 'Caption')
    d.new_page(width=595, height=842).insert_text((72, 100), 'End')
    d.save(p)
    result = audit_pdf(p)
    assert not result['pages'][0]['needs_review']
    assert result['pages'][0]['largest_gap_pt'] < 30
