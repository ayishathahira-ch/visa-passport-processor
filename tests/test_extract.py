from visa_processor import extract, mrz

# ICAO 9303 specimen passport (publicly documented fictional data, not a real person)
L1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
L2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
SPECIMEN_TEXT = f"REPUBLIC OF UTOPIA\nPassport\n{L1}\n{L2}\n"


def test_check_digit_known_values():
    assert mrz.check_digit("L898902C3") == 6
    assert mrz.check_digit("740812") == 2
    assert mrz.check_digit("120415") == 9


def test_parse_specimen_mrz():
    r = mrz.parse_mrz_from_text(SPECIMEN_TEXT)
    assert r["checks_ok"], r["checks"]
    assert r["full_name"] == "ANNA MARIA ERIKSSON"
    assert r["passport_number"] == "L898902C3"
    assert r["nationality"] == "UTO"
    assert r["date_of_birth"] == "1974-08-12"
    assert r["expiry_date"] == "2012-04-15"
    assert r["gender"] == "F"


def test_corrupted_mrz_fails_checks():
    bad = SPECIMEN_TEXT.replace("L898902C3", "L898902C4")
    assert not mrz.parse_mrz_from_text(bad)["checks_ok"]


def test_mrz_path_used_and_expiry_flagged():
    r = extract.extract_passport_info(SPECIMEN_TEXT, api_key="")
    assert r["extraction_method"] == "mrz"
    assert "passport is expired" in r["warnings"]  # specimen expired in 2012
    assert r["is_valid"] is False
    assert r["missing_fields"] == []


def test_regex_passport_number_label_regression():
    # old pattern `Passport(?: No|Number)?` captured "Number" from "Passport Number: ..."
    text = "Passport Number: AB1234567\nNationality: INDIAN\n"
    assert extract.extract_with_regex(text)["passport_number"] == "AB1234567"


def test_regex_ignores_stray_word_after_passport():
    assert extract.extract_with_regex("Passport of the Republic")["passport_number"] == ""


def test_regex_full_label_extraction():
    text = (
        "Surname: Rahman\nGiven Names: Sara\nNationality: Indian\n"
        "Date of Birth: 01/02/1995\nDate of Expiry: 01/02/2099\nSex: F\nPassport No: K1234567\n"
    )
    r = extract.extract_passport_info(text, api_key="")
    assert r["extraction_method"] == "regex"
    assert r["full_name"] == "Sara Rahman"
    assert r["gender"] == "F"
    assert r["is_valid"] is True


def test_missing_fields_make_record_invalid():
    r = extract.extract_passport_info("Surname: Only\n", api_key="")
    assert r["is_valid"] is False
    assert "passport_number" in r["missing_fields"]


def test_mrz_repairs_typical_tesseract_errors():
    # real Tesseract output: '<' read as 'c'/'e' in the filler, letter O read as digit 0
    noisy = (
        "P<UTONAIR<<MEERA<LAKSHMI<<<<<<<<<<<<<c<<<ec<<\n"
        "X1234567<7UT09203044F3106154<<<<<<<<<<<<<<06\n"
    )
    r = mrz.parse_mrz_from_text(noisy)
    assert r["checks_ok"], r["checks"]
    assert r["full_name"] == "MEERA LAKSHMI NAIR"
    assert r["nationality"] == "UTO"
    assert r["date_of_birth"] == "1992-03-04"
    assert r["expiry_date"] == "2031-06-15"
