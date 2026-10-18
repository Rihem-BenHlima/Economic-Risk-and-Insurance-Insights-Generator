# Data

**About the links.** The addresses below are the websites each dataset comes from. The exact download pages were not recorded in the files, so open the site and look for the dataset named in the table. The ones marked were found inside the data itself.

```
data/
├── API_TUN_DS2_en_csv_v2_17970/   World Bank indicators for Tunisia (raw download)
├── BCT/        Central Bank of Tunisia and INS files in the IMF template
├── CGA/        Insurance regulator: annual market tables
├── FAOSTAT/    Agriculture
├── FRED/       Macro series
├── FTUSA/      Insurers' federation: company and branch data, plus microfinance context
├── INS/        National statistics institute
├── OECD/       Insurance of other countries (comparison)
├── open-meteo/ Weather in Tunis
└── processed/  Cleaned tables made from all of the above (output of step_01_extraction)
```

## Sources and links

| Folder | Source | Link |
|---|---|---|
| API_TUN_DS2_en_csv_v2_17970 | World Bank, World Development Indicators (bulk CSV for Tunisia) | https://data.worldbank.org/country/tunisia |
| BCT | Banque Centrale de Tunisie (rates, exchange rates, money, trade) and INS through the BCT/IMF template | https://www.bct.gov.tn |
| CGA | Comité Général des Assurances, annual reports (Rapport annuel 2013 onwards) | https://www.cga.gov.tn |
| FAOSTAT | FAO statistics (crops, production indices, land) and World Bank agriculture indicators | https://www.fao.org/faostat |
| FRED | Federal Reserve Bank of St. Louis, macro series for Tunisia | https://fred.stlouisfed.org |
| FTUSA | Fédération Tunisienne des Sociétés d'Assurances, annual reports 2018 to 2024 (premiums, claims, cessions by company and branch) | https://www.ftusanet.org |
| FTUSA (microinsurance tables) | World Map of Microinsurance (from the files) | http://worldmapofmicroinsurance.org/ |
| INS | Institut National de la Statistique (inflation, GDP, population, labour) | https://www.ins.tn |
| OECD | OECD insurance statistics (global insurance indicators, premiums by class, underwriting) | https://data-explorer.oecd.org/ |
| open-meteo | Open-Meteo historical weather archive | https://open-meteo.com/en/docs/historical-weather-api |

## What is in each folder

### API_TUN_DS2_en_csv_v2_17970 (World Bank)
The raw World Bank download: about 1,500 indicators for Tunisia, one row per indicator and one column per year. Used for long GDP, inflation, unemployment, credit, trade and agriculture history before the other sources start.
- `API_TUN_DS2_en_csv_v2_17970.csv`: the indicator values.
- `Metadata_Country_...csv`: country information (region, income group).
- `Metadata_Indicator_...csv`: the definition and source of every indicator.

### BCT (central bank and INS template)
| File | Nature | Coverage |
|---|---|---|
| `cpi_all_items_monthly_2010_2026.csv` | Monthly consumer prices (2015 = 100) and yearly inflation; 7 months are missing in the source | 2010 to 2026 |
| `national_accounts_quarterly_2010_2026.csv` | Quarterly GDP and value added by sector, current and constant prices; some quarters are absent | 2010 to 2026 |
| `national_accounts_annual_current_prices_derived.csv` | Annual GDP built by summing four quarters (full years only) | partial |
| `monetary_aggregates_monthly_2001_2026.csv` | M1, M2, M3, net foreign assets, claims on the economy (private credit) | 2001 to 2026 |
| `trade_monthly_2014_2026.csv` | Monthly goods exports and imports, billion TND | 2014 to 2026 |
| `labour_annual_2011_2025.csv` | Employment and unemployment rate | 2011 to 2025 |
| `population_annual_2011_2024.csv` | Population, thousand persons | 2011 to 2024 |
| `bct_fx_interbank_snapshot_*.csv` | Interbank exchange rates, 20 currencies, **one day only** | snapshot |
| `bct_rates_snapshot_*.csv` | Policy rate, money market and savings rates, TUNIBOR, **one day only** | snapshot |
| `bct_macro_daily_snapshot_*.csv` | Tourism receipts, remittances, T-bills, key rate, a few days | snapshot |
| `data_dictionary.csv` | Description, unit, coverage and quirks of the BCT and INS files | |

### CGA (insurance regulator)
| File | Nature | Coverage |
|---|---|---|
| `tunisia_insurance_annual.csv` | **Main insurance table**: premiums and claims by branch (auto, health, life, fire, transport, agriculture and others), totals and growth rates | 2003 to 2024 |
| `tunisia_insurance_by_branch_long.csv` | The same figures in long format with the report each value came from | 2003 to 2024 |
| `tunisia_insurers_premiums.csv` | Premiums and market share by insurance company | 2014 to 2024 |
| `tunisia_insurance_companies_2022.csv` | One-year company snapshot: premiums, claims, provisions, own funds, staff | 2022 |
| `tunisia_agriculture_insurance.csv` | Agricultural insurance premiums, claims and cessions | 2003 onwards |
| `tunisia_distribution_channels.csv` | Share of premiums by channel (agents, brokers, banks and others) | few years |
| `peer_insurance_penetration.csv` | Insurance penetration (% of GDP) of Tunisia and peer countries | 2013 to 2024 |
| `world_insurance_markets.csv` | World and country premiums, density and penetration | 2013 to 2023 |
| `merge_log.csv` | Log of values that differed between report editions and which one was kept | |

### FAOSTAT (agriculture)
- `agri_production_indices.csv`: production indices (2014 to 2016 = 100) for agriculture, crops, livestock, food, cereals, olives, meat, milk and eggs, 2012 to 2024.
- `agri_crops_annual.csv`: area, production and yield of barley, cereals, dates, olive oil, olives, oranges, potatoes, tomatoes and wheat, 2012 to 2024.
- `agri_context_annual.csv`: agriculture's share of GDP and employment, land use, temperature anomaly and food prices, 2012 to 2024.

### FRED
- `macro_fred_annual.csv`: GDP per capita (constant US dollars), inflation, government net lending, current account, money growth and old-age dependency, 2012 to 2024.

### FTUSA (insurers' federation)
| File | Nature | Coverage |
|---|---|---|
| `ftusa_company_level_premiums_and_claims_2016_2024.csv` | Premiums and claims by company and branch, in DT (dinars). `ftusa_insurer_premiums_and_claims_by_company_and_branch_tunisia_2016_2024.csv` is the same table. | 2016 to 2024 |
| `ftusa_branch_level_premiums_claims_cessions_operating_account_1998_2024.csv` | Branch-level premiums, claims, cessions and operating account, with the report year each value came from | 1998 to 2024 |
| `ftusa_branch_level_premiums_claims_cessions_operating_account_2016_2024.csv` | The same, shorter period | 2016 to 2024 |
| `ftusa_market_indicators_1998_2024.csv` | Market indicators (sector split, financial position and others) | 1998 to 2024 |
| `ftusa_report_edition_corrections_log_tunisia_2018_2024.csv` | Corrections between report editions. `ftusa_2018_2024_report_restatements_and_typos_log.csv` is the same table. | 2018 to 2024 |
| `tunisia_*_2014/2015/2016.csv` (8 files) | Context for microinsurance and microfinance: ACM supervision, BCT refinancing rules, CARTE Vie client mix, 2016 finance law, IFC survey of small businesses, regulation thresholds, microinsurance coverage, mobile finance and labour | 2011 to 2016 |

Some files in this folder exist twice (a copy ending in ` (1)` or with no extension). They have the same content.

### INS (national statistics institute)
- `cpi_annual.csv`, `cpi_monthly_2026.csv`: consumer prices and inflation by category.
- `gdp_by_sector_quarterly.csv`, `gdp_real_growth_yoy_quarterly.csv`: quarterly GDP by sector and real growth (2024Q3 to 2026Q2).
- `labour_quarterly.csv`: unemployment, graduate unemployment, employed and active population by sex.
- `job_requests_annual.csv`: job requests registered at the national employment agency (ANETI), 2016 to 2024.
- `population_national.csv`, `population_by_governorate.csv`, `population_by_age_group.csv`: population, 2016 to 2024.
- `data_dictionary.csv`: description, unit, coverage and quirks of each file.

### OECD
Insurance data for 66 countries, 2020 to 2024, used for comparison with other markets:
- `panel_insurance_indicators.csv`: density, penetration, gross premiums, retention and reinsurance share.
- `panel_premiums_by_class.csv`: premiums by class of insurance.
- `panel_underwriting.csv`: gross premiums, claims paid, loss ratio, expenses and commissions.

### open-meteo (weather in Tunis)
- `weather_tunis_daily.csv`: the supplied file, daily rain, temperatures, soil temperature and wind, 2020 to 2025.
- `weather_tunis_daily_openmeteo_download_2003_2025.csv`: a longer download from the Open-Meteo archive, 2003 to 2025, used to fill the years before 2020.
- `weather_tunis_annual.csv`: yearly rainfall, rain days, heavy-rain days and hot days from the supplied file.

### processed (made by the project)
Created by `step_01_extraction/preprocessing/run_all.py` from the folders above. Gaps are filled only when two sources agree and nothing is guessed. The backend and the forecasting models read this folder.
- `modeling_table.csv`: **the one table the forecasting models use**: one row per year (2003 to 2024) with insurance, economy, labour, agriculture and climate columns.
- `insurance_annual.csv`, `insurance_annual_from_2010.csv`, `insurance_companies.csv`
- `economy_annual.csv`, `economy_annual_from_2012.csv`, `economy_monthly.csv`, `economy_quarterly.csv`, `economy_cpi_monthly.csv`
- `labour_annual.csv`, `labour_quarterly.csv`
- `agriculture_annual.csv`, `agriculture_context_2012_2024.csv`, `agriculture_crops.csv`
- `climate_annual.csv`, `climate_monthly.csv`, `climate_daily.csv`
- `preprocessing_log.csv` (every fill, chain-link and removal) and `audit_report.csv` (checks on the result).
