package db

import (
	"context"
	"fmt"
	"os"
	"sync/atomic"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// Client represents a PostgreSQL database client
type Client struct {
	pool      *pgxpool.Pool
	nextRunID uint64
}

// Run represents a benchmark run
type Run struct {
	ID         string   `json:"id"`
	Status     string   `json:"status"`
	Model      string   `json:"model"`
	Runtimes   []string `json:"runtimes"`
	ConfigYAML string   `json:"config_yaml"`
	HTMLUrl    string   `json:"html_url"`
	CSVUrl     string   `json:"csv_url"`
	RawUrl     string   `json:"raw_url"`
}

// NewClient creates a new database client
func NewClient(ctx context.Context) (*Client, error) {
	// Get database connection string from environment variable
	connString := os.Getenv("DATABASE_URL")
	if connString == "" {
		connString = "postgres://postgres:postgres@localhost:5432/tokenforge"
	}

	// Create connection pool
	config, err := pgxpool.ParseConfig(connString)
	if err != nil {
		return nil, fmt.Errorf("failed to parse connection string: %w", err)
	}

	pool, err := pgxpool.NewWithConfig(ctx, config)
	if err != nil {
		return nil, fmt.Errorf("failed to create connection pool: %w", err)
	}

	// Test connection
	if err := pool.Ping(ctx); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	// Initialize next run ID
	var maxID uint64
	err = pool.QueryRow(ctx, "SELECT COALESCE(MAX(CAST(SUBSTRING(id FROM 5) AS INTEGER)), 0) FROM runs").Scan(&maxID)
	if err != nil {
		return nil, fmt.Errorf("failed to get max run ID: %w", err)
	}

	return &Client{
		pool:      pool,
		nextRunID: maxID + 1,
	}, nil
}

// Close closes the database connection pool
func (c *Client) Close() {
	if c.pool != nil {
		c.pool.Close()
	}
}

// GetNextRunID gets the next run ID and increments the counter
func (c *Client) GetNextRunID() uint64 {
	return atomic.AddUint64(&c.nextRunID, 1) - 1
}

// CreateRun creates a new benchmark run
func (c *Client) CreateRun(ctx context.Context, id, status, model string, runtimes []string, configPath string) error {
	// Read config YAML
	configYAML, err := os.ReadFile(configPath)
	if err != nil {
		return fmt.Errorf("failed to read config YAML: %w", err)
	}

	// Insert run
	_, err = c.pool.Exec(
		ctx,
		"INSERT INTO runs (id, status, model, runtimes, config_yaml) VALUES ($1, $2, $3, $4, $5)",
		id, status, model, runtimes, string(configYAML),
	)
	if err != nil {
		return fmt.Errorf("failed to insert run: %w", err)
	}

	return nil
}

// UpdateRunStatus updates the status of a benchmark run
func (c *Client) UpdateRunStatus(ctx context.Context, id, status string, htmlURL, csvURL, rawURL *string) error {
	// Build query
	query := "UPDATE runs SET status = $1"
	args := []interface{}{status, id}
	argIndex := 3

	if htmlURL != nil {
		query += fmt.Sprintf(", html_url = $%d", argIndex)
		args = append(args, *htmlURL)
		argIndex++
	}

	if csvURL != nil {
		query += fmt.Sprintf(", csv_url = $%d", argIndex)
		args = append(args, *csvURL)
		argIndex++
	}

	if rawURL != nil {
		query += fmt.Sprintf(", raw_url = $%d", argIndex)
		args = append(args, *rawURL)
		argIndex++
	}

	query += " WHERE id = $2"

	// Execute query
	_, err := c.pool.Exec(ctx, query, args...)
	if err != nil {
		return fmt.Errorf("failed to update run status: %w", err)
	}

	return nil
}

// GetRun gets a benchmark run by ID
func (c *Client) GetRun(ctx context.Context, id string) (*Run, error) {
	var run Run

	err := c.pool.QueryRow(
		ctx,
		"SELECT id, status, model, runtimes, config_yaml, html_url, csv_url, raw_url FROM runs WHERE id = $1",
		id,
	).Scan(
		&run.ID,
		&run.Status,
		&run.Model,
		&run.Runtimes,
		&run.ConfigYAML,
		&run.HTMLUrl,
		&run.CSVUrl,
		&run.RawUrl,
	)
	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get run: %w", err)
	}

	return &run, nil
}

// ListRuns lists benchmark runs with pagination
func (c *Client) ListRuns(ctx context.Context, limit, offset int) ([]*Run, error) {
	rows, err := c.pool.Query(
		ctx,
		"SELECT id, status, model, runtimes, config_yaml, html_url, csv_url, raw_url FROM runs ORDER BY created_at DESC LIMIT $1 OFFSET $2",
		limit, offset,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to list runs: %w", err)
	}
	defer rows.Close()

	var runs []*Run
	for rows.Next() {
		var run Run
		err := rows.Scan(
			&run.ID,
			&run.Status,
			&run.Model,
			&run.Runtimes,
			&run.ConfigYAML,
			&run.HTMLUrl,
			&run.CSVUrl,
			&run.RawUrl,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan run: %w", err)
		}
		runs = append(runs, &run)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating rows: %w", err)
	}

	return runs, nil
}
