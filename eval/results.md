# Evaluation results (live model: claude-sonnet-5-5, 2026-11-09)

**Score: 19/20**

| Level | Passed |
|---|---|
| easy | 4/4 |
| medium | 8/8 |
| hard | 5/6 |
| refuse | 2/2 |

| id   | level   | pass   |   attempts |   secs | question                                                                                 |
|:-----|:--------|:-------|-----------:|-------:|:-----------------------------------------------------------------------------------------|
| q01  | easy    | ✅      |          1 |    1.3 | What were total net sales across the whole period?                                       |
| q02  | easy    | ✅      |          1 |    1.9 | What were net sales and gross margin percentage for each year?                           |
| q03  | easy    | ✅      |          1 |    1.2 | How many orders were placed in 2025, excluding cancelled ones?                           |
| q04  | easy    | ✅      |          1 |    1.5 | What share of items were cancelled?                                                      |
| q05  | medium  | ✅      |          1 |    1.5 | Which 5 categories generated the most gross profit in 2025?                              |
| q06  | medium  | ✅      |          1 |    1.8 | What is net sales by department (Men vs Women) for 2024?                                 |
| q07  | medium  | ✅      |          1 |    2.2 | Which traffic source has the highest average order value?                                |
| q08  | medium  | ✅      |          1 |    1.8 | What is the return rate by category? Show the 3 categories with the highest return rate. |
| q09  | medium  | ✅      |          1 |    4.1 | Which country had the most customers who bought something?                               |
| q10  | medium  | ✅      |          1 |    2   | Which distribution center ships fastest on average?                                      |
| q11  | medium  | ✅      |          1 |    1.3 | What were monthly net sales in 2025?                                                     |
| q12  | medium  | ✅      |          1 |    1.6 | Who are the top 3 brands by net sales in the Jeans category?                             |
| q13  | hard    | ✅      |          1 |    2.6 | By how much did net sales grow from 2024 to 2025, in percent?                            |
| q14  | hard    | ✅      |          1 |    1.5 | What were total net sales from customers in Spain?                                       |
| q15  | hard    | ✅      |          1 |    1.6 | Which category has the lowest gross margin percentage?                                   |
| q16  | hard    | ❌      |          1 |    2.4 | In 2025, which month had the highest return rate, and what was it?                       |
| q17  | hard    | ✅      |          1 |    5   | What share of 2025 net sales came from the top 10 brands?                                |
| q18  | hard    | ✅      |          1 |    2.2 | How many customers placed more than one non-cancelled order?                             |
| q19  | refuse  | ✅      |          1 |    1.4 | How much did we spend on marketing in 2025, and what was the return on it?               |
| q20  | refuse  | ✅      |          1 |    1.2 | What was the average customer satisfaction score by category?                            |

## Failures
- **q16** In 2025, which month had the highest return rate, and what was it? — wrong result

### Note on q16
The failing query from this run wasn't logged (the harness now saves the SQL and result of every failure). Asked again right after the run, the same model answered q16 correctly (February 2025, 12.9%). So the miss is about consistency between runs, not a gap in the definitions. The next step is a larger evaluation with several runs per question to measure that.
