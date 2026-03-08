@echo off
echo ============================================================
echo Testing Mentorship Report with Fixes
echo ============================================================
echo.

cd /d "d:\UAE Project"

echo [TEST] Running complete flow test...
python test_complete_flow.py

echo.
echo ============================================================
echo Test completed. Check output above for results.
echo ============================================================
pause
