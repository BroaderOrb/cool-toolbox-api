create index if not exists idx_asset_quotes_asset_quote_ts
  on asset_quotes(asset_id, quote_id, ts);

-- seed common quotes
insert into quotes(code, name, decimals) values
  ('USD','US Dollar',2),
  ('GBP','Pound Sterling',2),
  ('EUR','Euro',2)
on conflict (code) do nothing;

-- seed coingecko in sources
insert into sources(name, base_url) values
  ('coingecko','https://api.coingecko.com/api/v3')
on conflict (name) do nothing;
