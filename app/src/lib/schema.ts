export const SCHEMA = `
promotions(id, name)
show_series(id, name, promotion_id)
shows(id, show_series_id, promotion_id, event_date DATE, location, venue, is_ppv INT -- 0 or 1, attendance INT)
wrestlers(id, cagematch_id INT, ring_name, gender, birth_date, nationality)
matches(id, show_id, match_order INT, win_type TEXT -- "pinfall", "submission", "DQ", "count out", duration_seconds INT, match_type, title, is_title_match INT -- 0 or 1, rating_num REAL)
match_participants(id, match_id, cagematch_id INT, ring_name, result TEXT -- "win", "loss", or "draw")
title_reigns(id, wrestler_name, title_name, won_date DATE, lost_date DATE, days_held INT, won_event, lost_to)
factions(id, name, era)
faction_members(faction_id, cagematch_id INT, ring_name)
`;
