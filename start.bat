@echo off
rem --- Configure your search parameters here ---

rem 1. Research categories (required, one or more, separated by spaces)
SET CATEGORIES=cs.AI cs.CV stat.ML

rem 2. Keywords (optional, set to empty if not needed: SET KEYWORDS=)
rem    Note: Keywords with spaces must be enclosed in double quotes, e.g., "diffusion model"
SET KEYWORDS=llm multi-agent

rem 3. Target date (optional, format: YYYY-MM-DD)
rem    If left empty (SET TARGET_DATE=), the script will automatically search for yesterday's papers.
SET TARGET_DATE=


rem --- Execution Area ---
echo Configuration loaded, preparing to execute Python script...

rem Build command line arguments
SET ARGS=--categories %CATEGORIES%

IF DEFINED KEYWORDS (
    SET ARGS=%ARGS% --keywords %KEYWORDS%
)

IF DEFINED TARGET_DATE (
    SET ARGS=%ARGS% --date %TARGET_DATE%
)

SET COMMAND=python arxiv_daily_fetcher.py %ARGS%

echo Command to be executed: %COMMAND%
echo -----------------------------------------

rem Execute command
%COMMAND%

echo -----------------------------------------
echo Script execution finished.
rem Pause so you can see the output
rem pause

