# 回测演示03：策略是5个交易日平均成交量最大的股票
# 策略表现评估指标

import warnings

import pandas as pd

import qlib
from qlib.config import REG_CN
from qlib.contrib.evaluate import backtest_daily, risk_analysis
from qlib.data import D

if __name__ == '__main__':
	warnings.filterwarnings('ignore')

	# 1. 初始化Qlib（使用中国A股市场配置）
	qlib.init(provider_uri='~/.qlib/qlib_data/cn_data', region=REG_CN)

	# 2. 定义时间范围和资产池
	start_time = '2025-01-01'
	end_time = '2025-12-31'
	market = 'csi300'
	start_cash = 100000  # 初始仓位 10 万

	# 3. 构造预测信号, 使用内置算子 Mean ($volume, 5)
	instruments = D.instruments(market)
	# 选取过去5个交易日平均成交量最大的股票
	fields = ['Mean($volume, 5)']
	pred_score = D.features(instruments, fields, start_time, end_time)

	# 重命名列名为 score 以符合策略要求
	pred_score.columns = ['score']
	pred_score = pred_score.dropna()

	# 4. 配置策略, 每天买入成交量均值最大的前 5 只股票
	# strategy_config 说明
	#   class: TopkDropoutStrategy
	#     * 用途：指定策略逻辑。它是 Qlib 最常用的内置策略，旨在保持持仓池中始终是预测分数最高的股票。
	#     * 逻辑：它不仅仅是买入前 N 名，还包含了一套**“末位淘汰”**的换仓机制。
	#   module_path: qlib.contrib.strategy
	#     * 用途：指明该策略类在 Qlib 源码仓库中的位置。Qlib 会根据此路径动态加载 TopkDropoutStrategy 类。
	#   kwargs (内部参数)：
	#     - signal: pred_score：
	#       * 用途：输入“预测信号”。这通常是你的模型（如 LightGBM 或 GRU）对全市场股票跑出的预测分（Score）。策略会根据这个分数从高到低排序。
	#     - topk: 5：
	#       * 用途：持仓上限。即你的投资组合中最多同时持有 5 只股票。
	#     - n_drop: 2：
	#       * 用途：换仓阈值（淘汰数）。这是该策略的精髓：
	#         * 每天收盘后，策略检查当前持有的 5 只票。
	#         * 如果某只持仓股在当天的全市场预测排名中，跌出了前 (topk + n_drop) 名（即跌出前 7 名），该策略就会触发卖出信号。
	#         * 腾出的仓位会补入当天排名最高且尚未持有的股票。
	#
	strategy_config = {
		'class': 'TopkDropoutStrategy',  # 	指定策略逻辑(Qlib 最常用的内置策略),保持持仓池中始终是预测分数最高的股票
		'module_path': 'qlib.contrib.strategy',  # 指明该策略类在 Qlib 源码仓库中的位置。Qlib 会根据此路径动态加载 TopkDropoutStrategy 类
		'kwargs': {  # 内部参数
			'signal': pred_score,  # 		输入"预测信号". 这通常是你的模型对全市场股票跑出的预测分(Score), 策略会根据这个分数从高到低排序
			'topk': 5,  # 					持仓上限 (投资组合中最多同时持有5只股票)
			'n_drop': 2,  # 				换仓阈值（淘汰数）
		},
	}
	# Step 1：读取当天所有股票的 pred_score。
	# Step 2：卖出排名掉出前 7 名的旧股票。
	# Step 3：如果持仓不足 5 只，按分数从高到低补齐。
	# Step 4：根据生成的买卖信号更新 positions 并记录在 report 中

	# 5. 执行回测
	# backtest_daily 封装了账户管理、交易执行和报告生成等底层细节，使用户能快速验证投资策略的有效性
	# backtest_daily 会自动处理每日下单、成交和持仓逻辑
	# 常见参数包括：
	# | 参数名称 | 类型 | 说明 |
	# | :--- | :--- | :--- |
	# | start_time | str/Timestamp | 回测开始日期，如 "2020-01-01" |
	# | end_time | str/Timestamp | 回测结束日期 |
	# | strategy | Strategy 对象 | 投资策略实例（如 TopkDropoutStrategy） |
	# | portfolio_metric_dict | dict (可选) | 用于存储多维度回测结果的字典 |
	# 通常返回两个对象：report_normal（包含每日收益、费用等指标的 DataFrame）和 positions_normal（包含每日持仓详情的 dict/DataFrame）
	# report, positions = backtest_daily(start_time=start_time, end_time=end_time, strategy=strategy_config)
	report_normal, positions_normal = backtest_daily(start_time=start_time, end_time=end_time, strategy=strategy_config)
	analysis = dict()
	analysis['excess_return_without_cost'] = risk_analysis(
		report_normal['return'] - report_normal['bench'],
	)
	analysis['excess_return_with_cost'] = risk_analysis(report_normal['return'] - report_normal['bench'] - report_normal['cost'])

	analysis_df = pd.concat(analysis)  # type: pd.DataFrame
	print(analysis_df)
	# 数据分为两组：without_cost（未扣除交易成本，理想情况）和 with_cost（扣除交易成本，更接近实盘）。
	# 指标名称           含义          详细解释
	# mean	            日均超额收益   策略每日收益减去基准每日收益后的平均值。数值越高代表策略选股能力越强。
	# std	            超额收益标准差  衡量超额收益的波动程度，即“跟踪误差”（Tracking Error）。数值越小，表现越稳定。
	# annualized_return	年化超额收益   将日均超额收益转化为年度百分比。在 Qlib 中，它是基于算术累加（Arithmetic Summation）计算的，以避免几何累积产生的指数偏差。
	# information_ratio	信息比率 (IR)  计算公式为 mean / std 的年化值。衡量单位风险换取的超额收益。IR > 1 通常被认为是非常优秀的策略。
	# max_drawdown	    最大回撤       策略超额收益曲线从最高点下跌到最低点的最大跌幅（负数）。反映了策略在最坏情况下的亏损风险。
	#                                                   risk
	# excess_return_without_cost mean               0.000807
	#                            std                0.011454
	#                            annualized_return  0.192001
	#                            information_ratio  1.086539
	#                            max_drawdown      -0.196352
	# excess_return_with_cost    mean               0.000663
	#                            std                0.011460
	#                            annualized_return  0.157719
	#                            information_ratio  0.892054
	#                            max_drawdown      -0.211334

	# 6. 查看最简单的结果, 累计收益率
	# 累计收益率 = (1 + r1) * (1 + r2) * ... * (1 + rn) - 1
	cumulative_rate = (1 + report_normal['return']).prod() - 1  # 	累计收益率
	final_profit = start_cash * cumulative_rate  # 			绝对收益金额
	final_value = start_cash + final_profit  # 				期末总资产
	print('-' * 50)
	print(f'累计收益率：{cumulative_rate:.2f} %')
	print(f'绝对收益金额：{final_profit:.2f} 元')
	print(f'期末总资产：{final_value:.2f} 元')
	# 计算年化收益率 (假设一年252个交易日)
	print(f'年化收益率：{(report_normal["return"].mean() * 252):.2f} %')
