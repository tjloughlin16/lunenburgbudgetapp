/** HOMES AND THE TAX BILL AGAINST INFLATION, on /homes-and-taxes/growth-and-tax-rate: the historical
 *  report's own chart (components/HistoricalCharts.tsx HistoricalHomes), so the two pages draw one
 *  component from one set of figures -- scripts/build_historical_report.py homes(), passed through
 *  scripts/build_growth_rate_topic.py as this block's data. */
import type { CustomProps } from './index'
import { HistoricalHomes, type Homes } from '../../HistoricalCharts'

export default function HomesAgainstInflation({ data }: CustomProps) {
  return <HistoricalHomes h={data as Homes} />
}
