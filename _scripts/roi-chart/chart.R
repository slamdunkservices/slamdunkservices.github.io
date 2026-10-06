# Draws the homepage cumulative-units chart. Args: daily CSV, output PNG, 2022-23 scale factor.
suppressMessages({library(ggplot2); library(readr); library(dplyr)})
args <- commandArgs(TRUE); infile <- args[1]; outfile <- args[2]; scale_2223 <- as.numeric(args[3])
d <- read_csv(infile, show_col_types = FALSE) %>%
  mutate(net = if_else(series == "NBA 2022-23", net * scale_2223, net)) %>%
  group_by(date) %>% summarise(net = sum(net), .groups = "drop") %>%
  arrange(date) %>% mutate(cum = cumsum(net))
cat(sprintf("%s: end %s at %.1f units\n", outfile, max(d$date), tail(d$cum, 1)))
p <- ggplot(d, aes(date, cum)) +
  geom_line(colour = "#2ecc40", linewidth = 1.3) +
  scale_y_continuous(breaks = seq(0, 9000, 1500), labels = scales::comma, expand = expansion(mult = c(0.03, 0.05))) +
  scale_x_date(date_breaks = "6 months", date_labels = "%b %Y") +
  labs(x = NULL, y = NULL) +
  theme_minimal(base_size = 15) +
  theme(panel.grid.minor = element_blank(),
        panel.grid.major = element_line(colour = "#e5e5e5", linewidth = 0.8),
        axis.text = element_text(face = "bold", colour = "#3a3a3a"),
        axis.text.x = element_text(angle = 45, hjust = 1),
        plot.background = element_rect(fill = "white", colour = NA),
        plot.margin = margin(14, 18, 8, 8))
ggsave(outfile, p, width = 8, height = 4, dpi = 200, bg = "white")
