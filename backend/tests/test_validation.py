from pathlib import Path
from shutil import copyfile

import openpyxl
import pytest

from app.engine.validators import validate_data

SEED = Path(__file__).resolve().parents[1] / 'app' / 'data' / 'seed.xlsx'


@pytest.mark.parametrize(('sheet', 'cell', 'value', 'message'), [
    ('Farms', 'A5', None, 'Missing farm_id'),
    ('Farms', 'D5', 1.2, 'between 0 and 1'),
    ('Farms', 'H5', 7, 'multiple of 5'),
    ('Clients', 'C5', 'UNKNOWN', 'Invalid acceptance_mode'),
    ('Station', 'B5', 499, 'multiple of 5'),
])
def test_invalid_workbook_rejected(tmp_path, sheet, cell, value, message):
    path = tmp_path / 'invalid.xlsx'
    copyfile(SEED, path)
    wb = openpyxl.load_workbook(path)
    wb[sheet][cell] = value
    wb.save(path)
    with pytest.raises(ValueError, match=message):
        validate_data(path)
