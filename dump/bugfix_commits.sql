SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

CREATE DATABASE IF NOT EXISTS `bugfix_commits` DEFAULT CHARACTER SET latin1 COLLATE latin1_swedish_ci;
USE `bugfix_commits`;

CREATE TABLE IF NOT EXISTS `bug_commit` (
  `id` int(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `hash` varchar(40) CHARACTER SET utf8mb4 NOT NULL,
  `repository` varchar(300) CHARACTER SET utf8mb4 NOT NULL,
  `message` mediumtext CHARACTER SET utf8mb4 NOT NULL,
  `author` varchar(300) CHARACTER SET utf8mb4 NOT NULL,
  `url` varchar(300) CHARACTER SET utf8mb4 NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `bug_impacted_file` (
  `id` int(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` varchar(500) CHARACTER SET utf8mb4 NOT NULL,
  `new_path` varchar(500) CHARACTER SET utf8mb4,
  `old_path` varchar(500) CHARACTER SET utf8mb4,
  `lang` varchar(300) CHARACTER SET utf8mb4 NOT NULL,
  `lines_added` text CHARACTER SET utf8mb4 NOT NULL,
  `lines_deleted` text CHARACTER SET utf8 NOT NULL,
  `change_type` varchar(300) CHARACTER SET utf8mb4 NOT NULL,
  `commit_id` int(11) UNSIGNED NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_bug_commit_id` (`commit_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `fix_commit` (
  `id` int(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `hash` varchar(40) CHARACTER SET utf8mb4 NOT NULL,
  `repository` varchar(300) CHARACTER SET utf8mb4 NOT NULL,
  `message` mediumtext CHARACTER SET utf8mb4 NOT NULL,
  `author` varchar(300) CHARACTER SET utf8mb4 NOT NULL,
  `url` varchar(300) CHARACTER SET utf8mb4 NOT NULL,
  `created_at` datetime NOT NULL,
  `filter_introd` tinyint(1) NOT NULL,
  `introducing_commit_hash` varchar(40) CHARACTER SET utf8mb4 NOT NULL,
  `introducing_commit_id` int(11) UNSIGNED NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_bug_commit_id` (`introducing_commit_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS `fix_impacted_file` (
  `id` int(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` varchar(500) CHARACTER SET utf8mb4 NOT NULL,
  `new_path` varchar(500) CHARACTER SET utf8mb4,
  `old_path` varchar(500) CHARACTER SET utf8mb4,
  `lang` varchar(300) CHARACTER SET utf8mb4 NOT NULL,
  `lines_added` text CHARACTER SET utf8mb4 NOT NULL,
  `lines_deleted` text CHARACTER SET utf8 NOT NULL,
  `change_type` varchar(300) CHARACTER SET utf8mb4 NOT NULL,
  `commit_id` int(11) UNSIGNED NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_fix_commit_id` (`commit_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;


ALTER TABLE `bug_impacted_file`
  ADD CONSTRAINT `fk_commit_id` FOREIGN KEY (`commit_id`) REFERENCES `bug_commit` (`id`);

ALTER TABLE `fix_commit`
  ADD CONSTRAINT `fk_bug_commit_id` FOREIGN KEY (`introducing_commit_id`) REFERENCES `bug_commit` (`id`);

ALTER TABLE `fix_impacted_file`
  ADD CONSTRAINT `fk_fix_commit_id` FOREIGN KEY (`commit_id`) REFERENCES `fix_commit` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
