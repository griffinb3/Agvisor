# Commodity Risk Management Reference

## Futures Contracts Basics

### Grain & Oilseed Contracts (CME Group / CBOT)
- **Corn (ZC)**: 5,000 bushels per contract, $12.50 per tick (1/4 cent), traded on CBOT. Contract months: Mar, May, Jul, Sep, Dec.
- **Soybeans (ZS)**: 5,000 bushels per contract, $12.50 per tick (1/4 cent), traded on CBOT. Contract months: Jan, Mar, May, Jul, Aug, Sep, Nov.
- **Soybean Meal (ZM)**: 100 short tons per contract, $10 per tick (10 cents/ton), traded on CBOT.
- **Soybean Oil (ZL)**: 60,000 pounds per contract, $6 per tick (1/100 cent/lb), traded on CBOT.
- **Wheat (ZW)**: 5,000 bushels per contract, $12.50 per tick (1/4 cent), traded on CBOT. Contract months: Mar, May, Jul, Sep, Dec.
- **KC Hard Red Winter Wheat (KE)**: 5,000 bushels, $12.50 per tick, traded on KCBT.

### Livestock Contracts (CME)
- **Live Cattle (LE)**: 40,000 pounds per contract, $10 per tick (2.5 cents/cwt), traded on CME. Contract months: Feb, Apr, Jun, Aug, Oct, Dec.
- **Feeder Cattle (GF)**: 50,000 pounds per contract, $12.50 per tick (2.5 cents/cwt), traded on CME. Contract months: Jan, Mar, Apr, May, Aug, Sep, Oct, Nov.
- **Lean Hogs (HE)**: 40,000 pounds per contract, $10 per tick (2.5 cents/cwt), traded on CME. Contract months: Feb, Apr, May, Jun, Jul, Aug, Oct, Dec.

### Dairy Contracts (CME)
- **Class III Milk (DC)**: 200,000 pounds per contract, $20 per tick (1 cent/cwt), traded on CME. All calendar months.
- **Class IV Milk (GDK)**: 200,000 pounds per contract, $20 per tick, traded on CME.
- **Cheese (CSC)**: 20,000 pounds per contract, $2 per tick, traded on CME.

## Options Strategies for Ag Producers

### Protective Puts (Price Floor)
- Producer buys put options on the relevant futures contract to establish a minimum selling price
- Net price floor = put strike price − premium paid ± basis
- Best used when: prices are historically high and downside protection is needed while retaining upside
- Select strike prices near or slightly below current futures to balance cost and protection

### Call Options for Input Costs
- Buy call options on corn, soybean meal, or energy to cap input costs (e.g., feed for livestock)
- Maximum cost = call strike price + premium paid ± basis
- Provides protection against rising input prices while benefiting if prices fall

### Collars (Fence Strategy)
- Simultaneously buy a put option (price floor) and sell a call option (price ceiling)
- Premium from sold call offsets cost of purchased put, reducing or eliminating net premium
- Locks in a price range; gives up upside above call strike
- Example: Buy $5.00 corn put, sell $5.80 corn call — establishes a $5.00–$5.80 price range

### Bear Put Spreads
- Buy a higher-strike put, sell a lower-strike put on same contract month
- Reduces net premium cost but caps maximum protection at the lower strike
- Useful when moderate downside protection is sufficient

## Basis Explained

### Definition
- Basis = Local Cash Price − Nearby Futures Price
- Typically quoted as "under" (negative) or "over" (positive) the futures price
- Example: Cash corn at $4.50 with Dec futures at $4.80 → basis is −$0.30 or "30 under"

### Basis Determinants
- Local supply and demand conditions
- Transportation costs to delivery points or export terminals
- Storage costs and availability
- Quality premiums or discounts
- Time of year (seasonality)

### Historical Basis Patterns
- Basis tends to narrow (strengthen) during harvest as local supply peaks, then may weaken post-harvest
- Track 3-year and 5-year average basis by delivery month and location
- Basis is generally more predictable than outright price levels
- Strongest basis typically occurs when local supplies are tight relative to demand

### Basis Risk
- Risk that basis changes unfavorably between when a hedge is placed and when it is lifted
- A perfect hedge eliminates price-level risk but retains basis risk
- Basis risk is typically smaller than outright price risk

### Basis Contracts
- Cash contract where price is set as a fixed basis level relative to a specified futures month
- Producer locks in a favorable basis and sets the futures price component later
- Useful when basis is historically strong but futures prices are low

## Hedging Strategies by Crop Type

### Pre-Harvest Hedging
- Sell futures or buy put options against expected production before harvest
- Begin hedging when production costs are covered and a target margin is achievable
- Common approach: hedge 10–30% of expected production at planting, scale up through growing season
- Use new-crop contract months (e.g., Dec corn, Nov soybeans)

### Storage (Post-Harvest) Hedging
- Sell deferred futures against grain in storage to lock in carry (storage return)
- Carry = deferred futures price − nearby futures price − storage costs
- Only store grain when carry exceeds variable storage costs
- Monitor basis to decide optimal time to sell stored grain

### Rolling Hedges
- Move a hedge from a nearby expiring contract to a deferred contract
- Typically done when the position is not yet ready to be offset with a cash sale
- Rolling cost = difference between nearby and deferred contract prices
- Watch for contango vs. backwardation effects on roll costs

## Livestock Hedging Strategies

### Feeder Cattle
- Stocker operators buy put options or sell feeder cattle futures to protect against price declines
- Consider using Livestock Risk Protection (LRP) insurance as an alternative
- Hedge placement timing: when cattle are placed on grass or backgrounding program

### Live Cattle
- Feedlot operators sell live cattle futures or buy puts against cattle on feed
- Hedge ratio: typically 1 contract per 40,000 lbs of expected market weight
- Place hedges when cattle are placed on feed; lift when cattle are sold
- Monitor fed cattle basis by region (typically −$1 to −$4 in major feeding areas)

### Lean Hogs
- Hog producers sell lean hog futures or buy puts against expected marketings
- Contract settles on the CME Lean Hog Index (2-day weighted average)
- Basis tends to be more variable than cattle; track packer-specific basis
- Hedge 4–6 months forward for farrow-to-finish operations

## Input Cost Risk Management

### Fertilizer
- Forward contract with suppliers for anhydrous ammonia, UAN, DAP/MAP, potash
- Lock in prices during summer fill programs (June–August) for fall/spring application
- No liquid futures market; rely on forward contracting and supplier relationships
- Consider split purchases: lock a portion early, buy remaining closer to application

### Fuel
- Use NYMEX ULSD (heating oil) or RBOB gasoline futures/options as proxy hedges for diesel
- Heating oil (HO) contract: 42,000 gallons, $4.20 per tick
- Fuel hedging is a cross-hedge; basis between farm diesel and NYMEX can vary
- Farm fuel cooperatives sometimes offer fixed-price programs

### Feed
- Livestock producers hedge corn and soybean meal purchases using CBOT futures/options
- Crush spread: buy soybeans futures, sell soybean meal and oil futures to lock processing margins
- Feed cost hedging timeline: hedge 3–6 months forward based on placement schedules

## Margin Management Approach

### Cost of Production + Target Margin
- Calculate total cost per unit (bushel, hundredweight) including direct, overhead, land, and family living costs
- Set a target profit margin above breakeven (e.g., $0.50/bu corn, $5/cwt cattle)
- Trigger hedging actions when the market price exceeds cost of production + target margin
- Regularly update cost of production estimates as input costs change

### Breakeven Analysis
- Breakeven price = total costs ÷ expected yield (crops) or expected sale weight (livestock)
- Include: seed, chemicals, fertilizer, fuel, labor, machinery, land rent/mortgage, insurance, interest
- Separate fixed costs from variable costs to evaluate short-run vs. long-run breakeven
- Sensitivity analysis: model breakeven at different yield and cost scenarios

## Marketing Plan Framework

### Percentage-Based Pricing Targets
- Pre-set price levels at which specific percentages of production are sold
- Example plan for corn: sell 10% above $5.00, 15% above $5.25, 20% above $5.50, etc.
- Never market 100% before harvest — retain flexibility for production uncertainty
- Recommended maximum pre-harvest sales: 50–70% of expected production

### Seasonal Pricing Patterns
- Corn/Soybeans: prices often rally Feb–Jun (weather premium), weaken Aug–Oct (harvest pressure)
- Wheat: winter wheat often sees spring rally (Apr–May); harvest pressure Jun–Jul
- Cattle: typically strongest prices in spring (Apr–May), weakest in fall (Oct–Nov)
- Hogs: summer demand supports Jun–Aug prices; seasonal low often Dec–Feb
- Dairy: Class III tends to peak in summer months with ice cream demand

### Plan Components
- Identify total expected production and cost of production
- Set price targets tied to profitability thresholds
- Assign percentages of production to each target
- Specify tools to use at each target (futures, options, cash contracts)
- Review and adjust plan monthly based on market conditions and crop/livestock status

## Cash Marketing Tools

### Forward Contracts
- Agreement to deliver a specified quantity at a fixed price on a future date
- Locks in both futures price and basis; no premium cost
- Risk: production shortfall may require buying out the contract at market price
- Best used when both price and basis are favorable

### Basis Contracts
- Fix the basis component; set the futures price later (before a specified deadline)
- Useful when basis is historically strong but the producer expects higher futures
- Risk: if futures decline, final price may be lower than expected

### Hedge-to-Arrive (HTA) Contracts
- Fix the futures price component; basis is set at delivery
- Allows producer to benefit from potential basis improvement
- Typically allows rolling to deferred futures months
- Risk: basis may weaken from expected levels

### Minimum Price Contracts
- Elevator combines a forward contract with a purchased call option
- Establishes a price floor with upside potential if futures rise
- Producer pays a service fee or premium embedded in the contract
- Effectively equivalent to buying a put option at the elevator level

## Key Commodity Market Seasonal Patterns

- **January–February**: New marketing year planning; South American crop weather focus for soybeans
- **March–April**: USDA Prospective Plantings report (late March) — major market mover; spring planting outlook
- **May–June**: Planting progress and weather premium season; prevent plant decisions; cattle demand builds
- **July–August**: Pollination period for corn (critical yield determinant); summer weather market; hog demand peaks
- **September–October**: Harvest pressure begins; basis typically widens; new-crop supplies enter market
- **November–December**: Post-harvest basis recovery potential; export demand focus; South American planting begins
- **Key USDA Reports**: WASDE (monthly), Grain Stocks (quarterly), Prospective Plantings (March), Acreage (June), Crop Production (monthly in season)

## Risk Metrics

### Value at Risk (VaR)
- Estimates the maximum expected loss over a given time period at a specified confidence level
- Example: 95% 1-day VaR of $50,000 means a 5% chance of losing more than $50,000 in one day
- Calculate using historical price volatility of the commodity being hedged
- Use for portfolio-level assessment of total commodity exposure

### Position Sizing
- Determine contract quantity: production volume ÷ contract size = number of contracts
- Example: 100,000 bushels of corn ÷ 5,000 bu/contract = 20 contracts for full hedge
- Adjust for expected yield variability — avoid over-hedging by using conservative yield estimates
- Margin requirement: initial margin per contract × number of contracts = total capital commitment

### Hedge Ratio Calculations
- Optimal hedge ratio = (correlation between cash and futures) × (σ_cash / σ_futures)
- A ratio of 1.0 means a full hedge; ratios below 1.0 indicate a partial hedge is optimal
- Cross-hedge ratios (e.g., hedging feed barley with corn futures) are typically below 1.0
- Recalculate periodically as correlations and volatilities shift over time

### Monitoring and Adjustment
- Mark positions to market daily; track cumulative hedge gains/losses vs. cash market changes
- Set margin call thresholds and maintain adequate liquidity in margin accounts
- Review hedge effectiveness quarterly: compare hedged revenue/cost vs. unhedged scenario
- Document all hedging decisions and rationale for compliance and continuous improvement
