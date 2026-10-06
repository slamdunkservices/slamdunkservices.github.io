# Draws one season's cumulative net units for a recap post. Args: daily CSV (date, period, units_standardized_net),
# output PNG, x-axis break spacing (e.g. "1 month"). The playoffs are shaded.
suppressMessages({library(ggplot2); library(readr); library(dplyr)})
a <- commandArgs(TRUE)
d <- read_csv(a[1], show_col_types = FALSE)
po <- d %>% filter(period == "Playoffs")
d <- d %>% group_by(date) %>% summarise(net = sum(units_standardized_net), .groups = "drop") %>% arrange(date) %>% mutate(cum = cumsum(net))
cat(sprintf("%s: %s to %s, end %.1f\n", a[2], min(d$date), max(d$date), tail(d$cum, 1)))
p <- ggplot(d, aes(date, cum))
if (nrow(po) > 0) {
  p <- p + annotate("rect", xmin = min(po$date) - 0.5, xmax = max(po$date) + 0.5, ymin = -Inf, ymax = Inf, fill = "#2ecc40", alpha = 0.08) +
    annotate("text", x = min(po$date), y = -Inf, label = "Playoffs →", hjust = 1.08, vjust = -0.8, fontface = "bold", colour = "#5a5a5a", size = 4.6)
}
p <- p + geom_hline(yintercept = 0, colour = "#bdbdbd", linewidth = 0.6) +
  geom_line(colour = "#2ecc40", linewidth = 1.3) +
  scale_y_continuous(labels = scales::comma, expand = expansion(mult = c(0.08, 0.06))) +
  scale_x_date(date_breaks = a[3], date_labels = "%b %Y") +
  labs(x = NULL, y = "Net units") +
  theme_minimal(base_size = 15) +
  theme(panel.grid.minor = element_blank(),
        panel.grid.major = element_line(colour = "#e5e5e5", linewidth = 0.8),
        axis.text = element_text(face = "bold", colour = "#3a3a3a"),
        axis.title.y = element_text(face = "bold", colour = "#3a3a3a", margin = margin(r = 8)),
        axis.text.x = element_text(angle = 45, hjust = 1),
        plot.background = element_rect(fill = "white", colour = NA),
        plot.margin = margin(14, 18, 8, 8))
ggsave(a[2], p, width = 8, height = 4, dpi = 200, bg = "white")
