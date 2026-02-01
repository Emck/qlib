# 回测演示01：策略是5个交易日平均成交量最大的股票
# 生成一张简单的 10 万资产走势图

import warnings

import matplotlib.pyplot as plt
import pandas as pd

import qlib
from qlib.config import REG_CN
from qlib.contrib.evaluate import backtest_daily
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
	# backtest_daily 会自动处理每日下单、成交和持仓逻辑
	report, positions = backtest_daily(start_time=start_time, end_time=end_time, strategy=strategy_config)

	# 6. 查看最简单的结果, 累计收益率
	# 累计收益率 = (1 + r1) * (1 + r2) * ... * (1 + rn) - 1
	cumulative_rate = (1 + report['return']).prod() - 1  # 	累计收益率
	final_profit = start_cash * cumulative_rate  # 			绝对收益金额
	final_value = start_cash + final_profit  # 				期末总资产
	print('-' * 50)
	print(f'累计收益率：{cumulative_rate:.2f} %')
	print(f'绝对收益金额：{final_profit:.2f} 元')
	print(f'期末总资产：{final_value:.2f} 元')
	# 计算年化收益率 (假设一年252个交易日)
	print(f'年化收益率：{(report["return"].mean() * 252):.2f} %')

	# 另一种计算方式
	# 将 10 万初始资金转换为“净值” (即 1.0 为起点)
	# Qlib 的 report["return"] 是日收益率，我们需要计算累计乘积
	equity = (1 + report['return']).cumprod()
	final_value = equity * start_cash
	print(f'年末最终总资产: {final_value.iloc[-1]:.2f} 元')

	# 6. 查看某一天的持仓明细（例如 2020-01-06）
	# positions 是一个 dict，key 是日期，value 是该日期的持仓对象
	sample_date = pd.Timestamp('2025-12-25')
	if sample_date in positions:
		pos_obj = positions[sample_date]
		print('-' * 50)
		print(f'日期: {sample_date} 的持仓详情:')
		# 获取持仓列表
		print(pos_obj.get_stock_list())

	# 6. 可视化分析
	# 一张简单的 10 万资产走势图
	report['equity'] = (1 + report['return']).cumprod()
	report['total_value'] = report['equity'] * start_cash
	plt.figure(figsize=(12, 6))
	report['total_value'].plot(title='2025 Year Strategy Equity (Initial 100k)', grid=True)
	plt.ylabel('Account Value (CNY)')
	plt.show()
