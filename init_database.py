#!/usr/bin/env python3
"""
WolfeDesk v0.4.3 Database Initialization
Creates all required tables for the trading system.
Idempotent - safe to run multiple times.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Initialize WolfeDesk database schema"""
    
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL not found in environment")
        
        # Parse connection string
        # Format: postgresql://user:password@host/database
        parts = self.db_url.replace('postgresql://', '').split('@')
        auth = parts[0].split(':')
        host_db = parts[1].split('/')
        
        self.db_config = {
            'user': auth[0],
            'password': auth[1] if len(auth) > 1 else '',
            'host': host_db[0].split(':')[0],
            'port': host_db[0].split(':')[1] if ':' in host_db[0] else '5432',
            'database': host_db[1]
        }
        
        logger.info(f"Initializing database: {self.db_config['database']} on {self.db_config['host']}")
    
    def connect(self):
        """Create database connection"""
        return psycopg2.connect(**self.db_config)
    
    def initialize(self):
        """Initialize all database tables"""
        try:
            conn = self.connect()
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Create schema version table
            self._create_schema_version(cursor)
            
            # Core trading tables
            self._create_accounts_table(cursor)
            self._create_positions_table(cursor)
            self._create_trades_table(cursor)
            
            # Compliance and risk tables
            self._create_compliance_events_table(cursor)
            self._create_risk_snapshots_table(cursor)
            self._create_daily_limits_table(cursor)
            
            # Strategy and performance tables
            self._create_strategy_performance_table(cursor)
            self._create_hibernation_events_table(cursor)
            self._create_attribution_table(cursor)
            
            # Correlation and news tables
            self._create_correlation_matrix_table(cursor)
            self._create_news_events_table(cursor)
            self._create_dxy_levels_table(cursor)
            
            # Audit and logging tables
            self._create_audit_log_table(cursor)
            self._create_immutable_events_table(cursor)
            self._create_council_decisions_table(cursor)
            
            # Angela override tables
            self._create_angela_commands_table(cursor)
            self._create_thesis_trades_table(cursor)
            
            # Configuration and state tables
            self._create_configuration_table(cursor)
            self._create_system_state_table(cursor)
            self._create_leader_election_table(cursor)
            
            # Performance tracking tables
            self._create_daily_performance_table(cursor)
            self._create_equity_curve_table(cursor)
            
            # Create indexes
            self._create_indexes(cursor)
            
            # Create views
            self._create_views(cursor)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info("Database initialization complete!")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _create_schema_version(self, cursor):
        """Track schema version"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version VARCHAR(20) PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            );
            
            INSERT INTO schema_version (version, description)
            VALUES ('0.4.3', 'WolfeDesk v0.4.3 initial schema')
            ON CONFLICT (version) DO NOTHING;
        """)
        logger.info("Created schema_version table")
    
    def _create_accounts_table(self, cursor):
        """Trading accounts table"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                account_id SERIAL PRIMARY KEY,
                broker VARCHAR(50) NOT NULL,
                account_number VARCHAR(100) UNIQUE NOT NULL,
                account_type VARCHAR(50) NOT NULL, -- LIVE, DEMO, FTMO_PHASE1, FTMO_PHASE2
                initial_balance DECIMAL(15,2) NOT NULL,
                current_balance DECIMAL(15,2) NOT NULL,
                current_equity DECIMAL(15,2) NOT NULL,
                currency VARCHAR(10) DEFAULT 'USD',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                active BOOLEAN DEFAULT TRUE,
                metadata JSONB DEFAULT '{}'::jsonb
            );
        """)
        logger.info("Created accounts table")
    
    def _create_positions_table(self, cursor):
        """Open positions tracking"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                position_id SERIAL PRIMARY KEY,
                account_id INTEGER REFERENCES accounts(account_id),
                broker_position_id VARCHAR(100) UNIQUE,
                symbol VARCHAR(20) NOT NULL,
                direction VARCHAR(10) NOT NULL, -- BUY, SELL
                quantity DECIMAL(15,5) NOT NULL,
                entry_price DECIMAL(15,5) NOT NULL,
                current_price DECIMAL(15,5),
                stop_loss DECIMAL(15,5),
                take_profit DECIMAL(15,5),
                entry_time TIMESTAMP WITH TIME ZONE NOT NULL,
                exit_time TIMESTAMP WITH TIME ZONE,
                exit_price DECIMAL(15,5),
                commission DECIMAL(10,2) DEFAULT 0,
                swap DECIMAL(10,2) DEFAULT 0,
                profit_loss DECIMAL(15,2),
                profit_loss_pct DECIMAL(8,4),
                risk_amount DECIMAL(15,2) NOT NULL,
                risk_pct DECIMAL(5,3) NOT NULL,
                strategy VARCHAR(100) NOT NULL,
                signal_strength VARCHAR(20),
                cluster_id VARCHAR(50),
                status VARCHAR(20) DEFAULT 'OPEN', -- OPEN, CLOSED, CANCELLED
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'::jsonb
            );
            
            CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
            CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
            CREATE INDEX IF NOT EXISTS idx_positions_entry_time ON positions(entry_time);
        """)
        logger.info("Created positions table")
    
    def _create_trades_table(self, cursor):
        """Completed trades history"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id SERIAL PRIMARY KEY,
                account_id INTEGER REFERENCES accounts(account_id),
                position_id INTEGER REFERENCES positions(position_id),
                symbol VARCHAR(20) NOT NULL,
                direction VARCHAR(10) NOT NULL,
                quantity DECIMAL(15,5) NOT NULL,
                entry_price DECIMAL(15,5) NOT NULL,
                exit_price DECIMAL(15,5) NOT NULL,
                entry_time TIMESTAMP WITH TIME ZONE NOT NULL,
                exit_time TIMESTAMP WITH TIME ZONE NOT NULL,
                duration_seconds INTEGER,
                commission DECIMAL(10,2) DEFAULT 0,
                swap DECIMAL(10,2) DEFAULT 0,
                gross_pnl DECIMAL(15,2) NOT NULL,
                net_pnl DECIMAL(15,2) NOT NULL,
                pnl_pct DECIMAL(8,4) NOT NULL,
                r_multiple DECIMAL(6,2),
                risk_amount DECIMAL(15,2) NOT NULL,
                risk_pct DECIMAL(5,3) NOT NULL,
                strategy VARCHAR(100) NOT NULL,
                signal_strength VARCHAR(20),
                exit_reason VARCHAR(100),
                max_favorable DECIMAL(15,2),
                max_adverse DECIMAL(15,2),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'::jsonb
            );
            
            CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
            CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy);
            CREATE INDEX IF NOT EXISTS idx_trades_exit_time ON trades(exit_time);
        """)
        logger.info("Created trades table")
    
    def _create_compliance_events_table(self, cursor):
        """Compliance guard events"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_events (
                event_id SERIAL PRIMARY KEY,
                event_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                prague_time TIMESTAMP WITH TIME ZONE NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                severity VARCHAR(10) NOT NULL, -- S1, S2, S3
                code VARCHAR(50) NOT NULL,
                breach_value DECIMAL(15,5),
                limit_value DECIMAL(15,5),
                description TEXT,
                cooldown_until TIMESTAMP WITH TIME ZONE,
                account_id INTEGER REFERENCES accounts(account_id),
                position_id INTEGER REFERENCES positions(position_id),
                resolved BOOLEAN DEFAULT FALSE,
                resolved_at TIMESTAMP WITH TIME ZONE,
                metadata JSONB DEFAULT '{}'::jsonb
            );
            
            CREATE INDEX IF NOT EXISTS idx_compliance_severity ON compliance_events(severity);
            CREATE INDEX IF NOT EXISTS idx_compliance_time ON compliance_events(event_time);
            CREATE INDEX IF NOT EXISTS idx_compliance_resolved ON compliance_events(resolved);
        """)
        logger.info("Created compliance_events table")
    
    def _create_risk_snapshots_table(self, cursor):
        """Risk metrics snapshots"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_snapshots (
                snapshot_id SERIAL PRIMARY KEY,
                snapshot_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                prague_date DATE NOT NULL,
                account_id INTEGER REFERENCES accounts(account_id),
                snapshot_equity DECIMAL(15,2) NOT NULL,
                open_positions INTEGER DEFAULT 0,
                total_risk DECIMAL(15,2) DEFAULT 0,
                daily_pnl DECIMAL(15,2) DEFAULT 0,
                daily_dd_pct DECIMAL(5,3) DEFAULT 0,
                max_dd_pct DECIMAL(5,3) DEFAULT 0,
                current_streak INTEGER DEFAULT 0,
                performance_state VARCHAR(20),
                risk_mode VARCHAR(20),
                current_risk_pct DECIMAL(5,3),
                metadata JSONB DEFAULT '{}'::jsonb
            );
            
            CREATE INDEX IF NOT EXISTS idx_risk_snapshots_prague ON risk_snapshots(prague_date);
            CREATE INDEX IF NOT EXISTS idx_risk_snapshots_time ON risk_snapshots(snapshot_time);
        """)
        logger.info("Created risk_snapshots table")
    
    def _create_daily_limits_table(self, cursor):
        """Daily loss limits tracking"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_limits (
                limit_id SERIAL PRIMARY KEY,
                prague_date DATE NOT NULL,
                account_id INTEGER REFERENCES accounts(account_id),
                starting_equity DECIMAL(15,2) NOT NULL,
                soft_limit_amount DECIMAL(15,2) NOT NULL,
                hard_limit_amount DECIMAL(15,2) NOT NULL,
                soft_limit_pct DECIMAL(5,3) NOT NULL,
                hard_limit_pct DECIMAL(5,3) NOT NULL,
                current_dd DECIMAL(15,2) DEFAULT 0,
                current_dd_pct DECIMAL(5,3) DEFAULT 0,
                soft_breach_time TIMESTAMP WITH TIME ZONE,
                hard_breach_time TIMESTAMP WITH TIME ZONE,
                trading_disabled BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(prague_date, account_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_daily_limits_date ON daily_limits(prague_date);
        """)
        logger.info("Created daily_limits table")
    
    def _create_strategy_performance_table(self, cursor):
        """Strategy performance tracking"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_performance (
                performance_id SERIAL PRIMARY KEY,
                strategy_name VARCHAR(100) NOT NULL,
                measurement_date DATE NOT NULL,
                total_trades INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                win_rate DECIMAL(5,3),
                total_pnl DECIMAL(15,2) DEFAULT 0,
                total_r DECIMAL(10,2) DEFAULT 0,
                avg_win DECIMAL(15,2),
                avg_loss DECIMAL(15,2),
                expectancy DECIMAL(10,4),
                sharpe_ratio DECIMAL(6,3),
                profit_factor DECIMAL(6,3),
                max_drawdown DECIMAL(15,2),
                current_drawdown DECIMAL(15,2),
                consecutive_wins INTEGER DEFAULT 0,
                consecutive_losses INTEGER DEFAULT 0,
                state VARCHAR(20), -- ACTIVE, HIBERNATING, PROBATION, DISABLED
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'::jsonb,
                UNIQUE(strategy_name, measurement_date)
            );
            
            CREATE INDEX IF NOT EXISTS idx_strategy_perf_name ON strategy_performance(strategy_name);
            CREATE INDEX IF NOT EXISTS idx_strategy_perf_date ON strategy_performance(measurement_date);
        """)
        logger.info("Created strategy_performance table")
    
    def _create_hibernation_events_table(self, cursor):
        """Strategy hibernation events"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hibernation_events (
                hibernation_id SERIAL PRIMARY KEY,
                strategy_name VARCHAR(100) NOT NULL,
                hibernation_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                wake_time TIMESTAMP WITH TIME ZONE,
                reason TEXT NOT NULL,
                hibernation_number INTEGER DEFAULT 1,
                duration_hours INTEGER,
                performance_snapshot JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_hibernation_strategy ON hibernation_events(strategy_name);
        """)
        logger.info("Created hibernation_events table")
    
    def _create_attribution_table(self, cursor):
        """Performance attribution"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attribution (
                attribution_id SERIAL PRIMARY KEY,
                attribution_date DATE NOT NULL,
                account_id INTEGER REFERENCES accounts(account_id),
                component VARCHAR(50) NOT NULL, -- ENTRY_ALPHA, EXIT_ALPHA, SPREAD_COST, etc
                impact_amount DECIMAL(15,2) NOT NULL,
                impact_pct DECIMAL(6,3),
                trade_count INTEGER DEFAULT 0,
                description TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'::jsonb
            );
            
            CREATE INDEX IF NOT EXISTS idx_attribution_date ON attribution(attribution_date);
            CREATE INDEX IF NOT EXISTS idx_attribution_component ON attribution(component);
        """)
        logger.info("Created attribution table")
    
    def _create_correlation_matrix_table(self, cursor):
        """Correlation matrices"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS correlation_matrix (
                matrix_id SERIAL PRIMARY KEY,
                calculation_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                window_days INTEGER NOT NULL,
                symbols TEXT[] NOT NULL,
                matrix_data JSONB NOT NULL,
                high_correlations JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_correlation_time ON correlation_matrix(calculation_time);
        """)
        logger.info("Created correlation_matrix table")
    
    def _create_news_events_table(self, cursor):
        """Economic news events"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_events (
                event_id SERIAL PRIMARY KEY,
                event_time TIMESTAMP WITH TIME ZONE NOT NULL,
                currency VARCHAR(10) NOT NULL,
                event_name VARCHAR(200) NOT NULL,
                impact VARCHAR(10) NOT NULL, -- HIGH, MEDIUM, LOW
                tier INTEGER NOT NULL, -- 1, 2, 3
                actual_value VARCHAR(50),
                forecast_value VARCHAR(50),
                previous_value VARCHAR(50),
                blackout_start TIMESTAMP WITH TIME ZONE NOT NULL,
                blackout_end TIMESTAMP WITH TIME ZONE NOT NULL,
                affected_symbols TEXT[],
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'::jsonb
            );
            
            CREATE INDEX IF NOT EXISTS idx_news_time ON news_events(event_time);
            CREATE INDEX IF NOT EXISTS idx_news_currency ON news_events(currency);
            CREATE INDEX IF NOT EXISTS idx_news_impact ON news_events(impact);
        """)
        logger.info("Created news_events table")
    
    def _create_dxy_levels_table(self, cursor):
        """DXY support/resistance levels"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dxy_levels (
                level_id SERIAL PRIMARY KEY,
                level_value DECIMAL(8,3) NOT NULL UNIQUE,
                level_strength VARCHAR(10) NOT NULL, -- MAJOR, MINOR
                last_test TIMESTAMP WITH TIME ZONE,
                respect_count INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Insert default levels
            INSERT INTO dxy_levels (level_value, level_strength) VALUES
                (90.00, 'MAJOR'),
                (92.50, 'MINOR'),
                (95.00, 'MAJOR'),
                (97.50, 'MINOR'),
                (100.00, 'MAJOR'),
                (102.50, 'MINOR'),
                (105.00, 'MAJOR'),
                (107.50, 'MINOR'),
                (110.00, 'MAJOR')
            ON CONFLICT (level_value) DO NOTHING;
        """)
        logger.info("Created dxy_levels table")
    
    def _create_audit_log_table(self, cursor):
        """General audit log"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id SERIAL PRIMARY KEY,
                log_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                prague_time TIMESTAMP WITH TIME ZONE NOT NULL,
                event_type VARCHAR(100) NOT NULL,
                event_data JSONB NOT NULL,
                user_id VARCHAR(100),
                ip_address INET,
                session_id VARCHAR(100),
                hash_prev VARCHAR(64),
                hash_curr VARCHAR(64),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(log_time);
            CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(event_type);
        """)
        logger.info("Created audit_log table")
    
    def _create_immutable_events_table(self, cursor):
        """Immutable event chain"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS immutable_events (
                event_id SERIAL PRIMARY KEY,
                event_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                event_type VARCHAR(100) NOT NULL,
                event_data JSONB NOT NULL,
                signature VARCHAR(256),
                hash_chain VARCHAR(64) NOT NULL,
                previous_hash VARCHAR(64),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_immutable_time ON immutable_events(event_time);
        """)
        logger.info("Created immutable_events table")
    
    def _create_council_decisions_table(self, cursor):
        """Council decision log"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS council_decisions (
                decision_id SERIAL PRIMARY KEY,
                decision_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                decision_type VARCHAR(100) NOT NULL,
                decision_data JSONB NOT NULL,
                risk_score DECIMAL(5,2),
                approved BOOLEAN NOT NULL,
                approver VARCHAR(100),
                signatures JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_council_time ON council_decisions(decision_time);
        """)
        logger.info("Created council_decisions table")
    
    def _create_angela_commands_table(self, cursor):
        """Angela's sovereign commands"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS angela_commands (
                command_id VARCHAR(100) PRIMARY KEY,
                command_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                override_type VARCHAR(50) NOT NULL,
                payload JSONB NOT NULL,
                signature TEXT,
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                executed BOOLEAN DEFAULT FALSE,
                execution_time TIMESTAMP WITH TIME ZONE,
                execution_result JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_angela_time ON angela_commands(command_time);
            CREATE INDEX IF NOT EXISTS idx_angela_executed ON angela_commands(executed);
        """)
        logger.info("Created angela_commands table")
    
    def _create_thesis_trades_table(self, cursor):
        """Angela's thesis trades"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS thesis_trades (
                thesis_id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                thesis TEXT NOT NULL,
                direction VARCHAR(10) NOT NULL,
                target_level DECIMAL(15,5) NOT NULL,
                confidence VARCHAR(10) NOT NULL,
                timeframe VARCHAR(50),
                entry_zones JSONB,
                stop_loss DECIMAL(15,5),
                take_profit DECIMAL(15,5),
                risk_amount DECIMAL(15,2),
                execution_strategy VARCHAR(100),
                entry_triggers TEXT[],
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                executed_at TIMESTAMP WITH TIME ZONE,
                closed_at TIMESTAMP WITH TIME ZONE,
                result JSONB
            );
            
            CREATE INDEX IF NOT EXISTS idx_thesis_symbol ON thesis_trades(symbol);
        """)
        logger.info("Created thesis_trades table")
    
    def _create_configuration_table(self, cursor):
        """System configuration"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuration (
                config_id SERIAL PRIMARY KEY,
                config_key VARCHAR(100) UNIQUE NOT NULL,
                config_value JSONB NOT NULL,
                config_type VARCHAR(50) NOT NULL,
                description TEXT,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_by VARCHAR(100),
                version INTEGER DEFAULT 1,
                active BOOLEAN DEFAULT TRUE
            );
            
            CREATE INDEX IF NOT EXISTS idx_config_key ON configuration(config_key);
        """)
        logger.info("Created configuration table")
    
    def _create_system_state_table(self, cursor):
        """System state tracking"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_state (
                state_id SERIAL PRIMARY KEY,
                node_id VARCHAR(100) NOT NULL,
                state_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                executor_mode VARCHAR(20) NOT NULL,
                is_leader BOOLEAN DEFAULT FALSE,
                angela_connected BOOLEAN DEFAULT FALSE,
                angela_override_active BOOLEAN DEFAULT FALSE,
                components_status JSONB NOT NULL,
                performance_state VARCHAR(20),
                active_strategies TEXT[],
                open_positions INTEGER DEFAULT 0,
                daily_pnl DECIMAL(15,2) DEFAULT 0,
                current_session VARCHAR(20),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_state_time ON system_state(state_time);
            CREATE INDEX IF NOT EXISTS idx_state_node ON system_state(node_id);
        """)
        logger.info("Created system_state table")
    
    def _create_leader_election_table(self, cursor):
        """Leader election for HA"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leader_election (
                election_id SERIAL PRIMARY KEY,
                node_id VARCHAR(100) NOT NULL,
                leader_since TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                ttl_seconds INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                metadata JSONB DEFAULT '{}'::jsonb
            );
            
            CREATE INDEX IF NOT EXISTS idx_leader_node ON leader_election(node_id);
            CREATE INDEX IF NOT EXISTS idx_leader_active ON leader_election(is_active);
        """)
        logger.info("Created leader_election table")
    
    def _create_daily_performance_table(self, cursor):
        """Daily performance summary"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_performance (
                performance_id SERIAL PRIMARY KEY,
                performance_date DATE NOT NULL,
                account_id INTEGER REFERENCES accounts(account_id),
                starting_equity DECIMAL(15,2) NOT NULL,
                ending_equity DECIMAL(15,2) NOT NULL,
                high_equity DECIMAL(15,2),
                low_equity DECIMAL(15,2),
                gross_pnl DECIMAL(15,2) NOT NULL,
                net_pnl DECIMAL(15,2) NOT NULL,
                commission_paid DECIMAL(10,2) DEFAULT 0,
                swap_paid DECIMAL(10,2) DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                max_drawdown DECIMAL(15,2),
                max_drawdown_pct DECIMAL(5,3),
                sharpe_ratio DECIMAL(6,3),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'::jsonb,
                UNIQUE(performance_date, account_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_daily_perf_date ON daily_performance(performance_date);
        """)
        logger.info("Created daily_performance table")
    
    def _create_equity_curve_table(self, cursor):
        """Equity curve tracking"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equity_curve (
                curve_id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                account_id INTEGER REFERENCES accounts(account_id),
                equity DECIMAL(15,2) NOT NULL,
                balance DECIMAL(15,2) NOT NULL,
                floating_pnl DECIMAL(15,2) DEFAULT 0,
                margin_used DECIMAL(15,2) DEFAULT 0,
                margin_free DECIMAL(15,2) DEFAULT 0,
                open_positions INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_equity_time ON equity_curve(timestamp);
            CREATE INDEX IF NOT EXISTS idx_equity_account ON equity_curve(account_id);
        """)
        logger.info("Created equity_curve table")
    
    def _create_indexes(self, cursor):
        """Create additional performance indexes"""
        index_commands = [
            "CREATE INDEX IF NOT EXISTS idx_positions_account ON positions(account_id)",
            "CREATE INDEX IF NOT EXISTS idx_trades_account ON trades(account_id)",
            "CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)",
            "CREATE INDEX IF NOT EXISTS idx_compliance_account ON compliance_events(account_id)",
            "CREATE INDEX IF NOT EXISTS idx_risk_account ON risk_snapshots(account_id)",
            "CREATE INDEX IF NOT EXISTS idx_attribution_account ON attribution(account_id)",
        ]
        
        for cmd in index_commands:
            cursor.execute(cmd)
        
        logger.info("Created performance indexes")
    
    def _create_views(self, cursor):
        """Create useful views"""
        
        # Current positions view
        cursor.execute("""
            CREATE OR REPLACE VIEW current_positions AS
            SELECT 
                p.*,
                a.broker,
                a.account_number,
                a.account_type
            FROM positions p
            JOIN accounts a ON p.account_id = a.account_id
            WHERE p.status = 'OPEN';
        """)
        
        # Today's trades view
        cursor.execute("""
            CREATE OR REPLACE VIEW todays_trades AS
            SELECT 
                t.*,
                a.broker,
                a.account_number
            FROM trades t
            JOIN accounts a ON t.account_id = a.account_id
            WHERE DATE(t.exit_time) = CURRENT_DATE;
        """)
        
        # Strategy performance summary view
        cursor.execute("""
            CREATE OR REPLACE VIEW strategy_summary AS
            SELECT 
                strategy_name,
                state,
                SUM(total_trades) as total_trades,
                AVG(win_rate) as avg_win_rate,
                SUM(total_pnl) as total_pnl,
                AVG(sharpe_ratio) as avg_sharpe,
                MAX(consecutive_wins) as max_win_streak,
                MAX(consecutive_losses) as max_loss_streak,
                MAX(measurement_date) as last_updated
            FROM strategy_performance
            WHERE measurement_date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY strategy_name, state;
        """)
        
        # Risk monitor view
        cursor.execute("""
            CREATE OR REPLACE VIEW risk_monitor AS
            SELECT 
                dl.prague_date,
                dl.account_id,
                a.account_number,
                dl.starting_equity,
                dl.current_dd,
                dl.current_dd_pct,
                dl.soft_limit_pct,
                dl.hard_limit_pct,
                dl.trading_disabled,
                COUNT(p.position_id) as open_positions,
                COALESCE(SUM(p.risk_amount), 0) as total_risk
            FROM daily_limits dl
            JOIN accounts a ON dl.account_id = a.account_id
            LEFT JOIN positions p ON p.account_id = dl.account_id AND p.status = 'OPEN'
            WHERE dl.prague_date = CURRENT_DATE
            GROUP BY dl.prague_date, dl.account_id, a.account_number, 
                     dl.starting_equity, dl.current_dd, dl.current_dd_pct,
                     dl.soft_limit_pct, dl.hard_limit_pct, dl.trading_disabled;
        """)
        
        logger.info("Created database views")


def main():
    """Initialize the database"""
    try:
        initializer = DatabaseInitializer()
        initializer.initialize()
        
        # Test connection
        conn = initializer.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT version, applied_at FROM schema_version ORDER BY applied_at DESC LIMIT 1")
        version, applied_at = cursor.fetchone()
        cursor.close()
        conn.close()
        
        print(f"\n{'='*60}")
        print(f"✅ WolfeDesk Database Initialized Successfully!")
        print(f"{'='*60}")
        print(f"Schema Version: {version}")
        print(f"Applied At: {applied_at}")
        print(f"Database: {initializer.db_config['database']}")
        print(f"Host: {initializer.db_config['host']}")
        print(f"{'='*60}")
        print("\nYou can now proceed with Step 5 of the deployment guide.")
        
    except Exception as e:
        print(f"\n❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()