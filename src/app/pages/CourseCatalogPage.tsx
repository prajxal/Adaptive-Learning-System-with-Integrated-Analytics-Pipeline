import React, { useState } from 'react';
import { Search, BookOpen, Clock, BarChart3, GraduationCap } from 'lucide-react';
import { Link } from 'react-router-dom';
import { LemonInput } from '../components/LemonInput';
import { LemonCard } from '../components/LemonCard';
import { Course } from '../data/courses';
import { ROUTES } from "../constants/routes";
import { useCourses } from '../../hooks/useCourses';
import { getCourseDifficultyInfo } from '../../lib/xpUtils';

interface CourseCatalogPageProps {
  onCourseSelect: (course: Course) => void;
}

export function CourseCatalogPage({ onCourseSelect }: CourseCatalogPageProps) {
  const [selectedCategory, setSelectedCategory] = useState('All Courses');
  const [searchQuery, setSearchQuery] = useState('');
  const { courses, loading, error } = useCourses();

  if (loading) {
    return <div>Loading courses...</div>;
  }

  if (error) {
    return <div>Error loading courses</div>;
  }

  const iconPalette = ['📚', '🧩', '🛠️', '⚙️', '🧠', '🔧', '🚀', '💡'];
  const colorPalette = [
    'bg-blue-500',
    'bg-indigo-500',
    'bg-cyan-500',
    'bg-emerald-500',
    'bg-orange-500',
    'bg-violet-500',
    'bg-rose-500',
    'bg-teal-500',
  ];

  const mappedCourses: Course[] = courses.map((course, index) => ({
    id: course.id,
    title: course.title,
    category: course.roadmap_id,
    description: `Roadmap: ${course.roadmap_id}`,
    icon: iconPalette[index % iconPalette.length],
    duration: 'Self-paced',
    level: getCourseDifficultyInfo(course.difficulty_level).label,
    topics: 0,
    color: colorPalette[index % colorPalette.length],
  }));

  const categories = ['All Courses', ...Array.from(new Set(mappedCourses.map((course) => course.category)))];

  const filteredCourses = mappedCourses.filter((course) => {
    const matchesCategory =
      selectedCategory === 'All Courses' || course.category === selectedCategory;
    const matchesSearch =
      searchQuery === '' ||
      course.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      course.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-slate-900 dark:to-slate-800 border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center max-w-3xl mx-auto space-y-6">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-accent/10 border border-accent/20 rounded-full">
              <GraduationCap className="w-5 h-5 text-accent" />
              <span className="font-medium text-accent">Engineering Learning Platform</span>
            </div>

            <h1 className="text-5xl sm:text-6xl font-medium tracking-tight">
              Master Engineering
              <br />
              <span className="text-accent">One Course at a Time</span>
            </h1>

            <p className="text-xl text-muted-foreground">
              AI-powered learning paths designed specifically for engineering students.
              Choose your course and start building your future.
            </p>

            {/* Search Bar */}
            <div className="max-w-2xl mx-auto mt-8">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <LemonInput
                  type="text"
                  placeholder="Search courses..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  size="large"
                  fullWidth
                  className="pl-11"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Category Filter */}
        <div className="mb-8">
          <div className="flex flex-wrap gap-2">
            {categories.map((category) => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={`
                  px-4 py-2 rounded-[6px] border transition-all font-medium
                  ${selectedCategory === category
                    ? 'bg-accent text-accent-foreground border-accent'
                    : 'bg-card text-foreground border-border hover:bg-secondary'
                  }
                `}
              >
                {category}
              </button>
            ))}
          </div>
        </div>

        {/* Course Count */}
        <div className="mb-6">
          <p className="text-muted-foreground">
            {filteredCourses.length} {filteredCourses.length === 1 ? 'course' : 'courses'} available
          </p>
        </div>

        {/* Courses Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCourses.map((course) => (
            <Link key={course.id} to={ROUTES.COURSE(course.id)} className="block">
              <LemonCard
                hoverable
                onClick={() => onCourseSelect(course)}
              >
                <div className="space-y-4">
                  {/* Course Icon & Category */}
                  <div className="flex items-start justify-between">
                    <div className={`w-14 h-14 ${course.color} rounded-[6px] flex items-center justify-center text-3xl`}>
                      {course.icon}
                    </div>
                    <span className="text-xs px-2 py-1 bg-secondary text-secondary-foreground rounded-full">
                      {course.category}
                    </span>
                  </div>

                  {/* Course Title & Description */}
                  <div>
                    <h3 className="font-medium mb-2">{course.title}</h3>
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {course.description}
                    </p>
                  </div>

                  {/* Course Meta */}
                  <div className="flex items-center gap-4 pt-4 border-t border-border text-sm text-muted-foreground">
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-4 h-4" />
                      <span>{course.duration}</span>
                    </div>
                    {course.topics > 0 && (
                      <div className="flex items-center gap-1.5">
                        <BookOpen className="w-4 h-4" />
                        <span>{course.topics} topics</span>
                      </div>
                    )}
                    <div className="flex items-center gap-1.5">
                      <BarChart3 className="w-4 h-4" />
                      <span>{course.level}</span>
                    </div>
                  </div>
                </div>
              </LemonCard>
            </Link>
          ))}
        </div>

        {/* No Results */}
        {filteredCourses.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="font-medium mb-2">No courses found</h3>
            <p className="text-muted-foreground">
              Try adjusting your search or filter to find what you're looking for.
            </p>
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div className="bg-secondary border-t border-border mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            <div>
              <p className="text-3xl font-medium text-foreground mb-1">16</p>
              <p className="text-sm text-muted-foreground">Expert Courses</p>
            </div>
            <div>
              <p className="text-3xl font-medium text-foreground mb-1">150+</p>
              <p className="text-sm text-muted-foreground">Learning Topics</p>
            </div>
            <div>
              <p className="text-3xl font-medium text-foreground mb-1">100%</p>
              <p className="text-sm text-muted-foreground">Free Access</p>
            </div>
            <div>
              <p className="text-3xl font-medium text-foreground mb-1">AI</p>
              <p className="text-sm text-muted-foreground">Powered Learning</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
