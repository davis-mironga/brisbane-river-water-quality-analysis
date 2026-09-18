#!/bin/bash
set -uo pipefail
PASS=0
FAIL=0
FAILED_CHECKS=()

check() {
    local name="$1"
    local result="$2"
    if [ "$result" -eq 0 ]; then
        echo "  PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $name"
        FAIL=$((FAIL + 1))
        FAILED_CHECKS+=("$name")
    fi
}

echo "============================================================"
echo "1. Git status"
echo "============================================================"
git fetch origin --quiet
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
if [ "$LOCAL" == "$REMOTE" ]; then
    echo "  Local main matches origin/main ($LOCAL)"
    check "Git in sync with origin/main" 0
else
    echo "  WARNING: local ($LOCAL) differs from origin/main ($REMOTE)"
    check "Git in sync with origin/main" 1
fi

echo ""
echo "============================================================"
echo "2. Executing Notebook 1 (data understanding & cleaning)"
echo "============================================================"
jupyter nbconvert --to notebook --execute notebooks/01_data_understanding_cleaning.ipynb \
    --output 01_data_understanding_cleaning.ipynb > /tmp/nb1_log.txt 2>&1
NB1_EXEC=$?
NB1_ERRORS=$(python3 -c "
import json
nb = json.load(open('notebooks/01_data_understanding_cleaning.ipynb'))
errors = sum(1 for c in nb['cells'] for o in c.get('outputs', []) if o.get('output_type') == 'error')
print(errors)
")
check "Notebook 1 executes without error" $([ "$NB1_EXEC" -eq 0 ] && [ "$NB1_ERRORS" -eq 0 ] && echo 0 || echo 1)

echo ""
echo "============================================================"
echo "3. Executing Notebook 2 (exploratory analysis)"
echo "============================================================"
jupyter nbconvert --to notebook --execute notebooks/02_exploratory_environmental_analysis.ipynb \
    --output 02_exploratory_environmental_analysis.ipynb > /tmp/nb2_log.txt 2>&1
NB2_EXEC=$?
NB2_ERRORS=$(python3 -c "
import json
nb = json.load(open('notebooks/02_exploratory_environmental_analysis.ipynb'))
errors = sum(1 for c in nb['cells'] for o in c.get('outputs', []) if o.get('output_type') == 'error')
print(errors)
")
check "Notebook 2 executes without error" $([ "$NB2_EXEC" -eq 0 ] && [ "$NB2_ERRORS" -eq 0 ] && echo 0 || echo 1)

echo ""
echo "============================================================"
echo "4. Executing Notebook 3 (environmental insights)"
echo "============================================================"
jupyter nbconvert --to notebook --execute notebooks/03_environmental_insights.ipynb \
    --output 03_environmental_insights.ipynb > /tmp/nb3_log.txt 2>&1
NB3_EXEC=$?
NB3_ERRORS=$(python3 -c "
import json
nb = json.load(open('notebooks/03_environmental_insights.ipynb'))
errors = sum(1 for c in nb['cells'] for o in c.get('outputs', []) if o.get('output_type') == 'error')
print(errors)
")
check "Notebook 3 executes without error" $([ "$NB3_EXEC" -eq 0 ] && [ "$NB3_ERRORS" -eq 0 ] && echo 0 || echo 1)

echo ""
echo "============================================================"
echo "5. Verifying key data facts"
echo "============================================================"
python3 << 'PYEOF'
import json, sys
nb = json.load(open('notebooks/01_data_understanding_cleaning.ipynb'))
found_30894 = False
for cell in nb['cells']:
    for out in cell.get('outputs', []):
        text = ''.join(out.get('text', [])) if 'text' in out else ''
        if '30,894' in text or '30894' in text:
            found_30894 = True
print("  30,894 rows referenced in Notebook 1 output:", found_30894)
sys.exit(0 if found_30894 else 1)
PYEOF
check "Notebook 1 confirms 30,894-row dataset" $?

echo ""
echo "============================================================"
echo "6. Rebuilding SQLite database and running all 4 SQL files"
echo "============================================================"
python3 -c "
import pandas as pd, sqlite3
df = pd.read_csv('data/processed/water_quality_cleaned.csv')
conn = sqlite3.connect('data/processed/water_quality.db')
df.to_sql('water_quality', conn, if_exists='replace', index=False)
conn.close()
print('  Rebuilt water_quality.db:', len(df), 'rows')
"
check "SQLite database rebuilt from cleaned CSV" $?

for sqlfile in sql/01_data_quality.sql sql/02_temporal_analysis.sql sql/03_water_quality_analysis.sql sql/04_environmental_insights.sql; do
    sqlite3 data/processed/water_quality.db < "$sqlfile" > /tmp/sql_out.txt 2>/tmp/sql_err.txt
    SQL_RESULT=$?
    if [ -s /tmp/sql_err.txt ]; then
        SQL_RESULT=1
    fi
    check "$sqlfile runs without error" $SQL_RESULT
done

echo ""
echo "============================================================"
echo "7. Running pytest suite (src/cleaning.py unit tests)"
echo "============================================================"
python3 -m pytest tests/ -q > /tmp/pytest_log.txt 2>&1
PYTEST_RESULT=$?
tail -5 /tmp/pytest_log.txt
check "All unit tests pass" $PYTEST_RESULT

echo ""
echo "============================================================"
echo "8. Verifying src/cleaning.py and src/analysis.py import cleanly"
echo "============================================================"
python3 -c "
import sys
sys.path.insert(0, 'src')
import cleaning, analysis
print('  Both modules imported successfully')
"
check "src/ modules import without error" $?

echo ""
echo "============================================================"
echo "SUMMARY"
echo "============================================================"
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
if [ $FAIL -eq 0 ]; then
    echo ""
    echo "  ALL CHECKS PASSED -- project is fully working end-to-end."
else
    echo ""
    echo "  FAILED CHECKS:"
    for f in "${FAILED_CHECKS[@]}"; do
        echo "    - $f"
    done
fi
